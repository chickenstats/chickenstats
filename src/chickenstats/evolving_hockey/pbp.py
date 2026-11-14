from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, overload

import polars as pl
import polars.selectors as cs

from chickenstats.chicken_nhl._game_utils import FENWICK_EVENTS, OPPOSING_PLAYER_2_EVENTS
from chickenstats.evolving_hockey import _weights
from chickenstats.chicken_nhl._validation_utils import coerce_to_schema
from chickenstats.evolving_hockey._agg_constants import TEAM_REPLACE
from chickenstats.evolving_hockey._names import eh_id_expr, name_key_expr, player_name_expr
from chickenstats.evolving_hockey.validation import PBPSchema
from chickenstats.exceptions import DataMismatchError, InvalidInputError
from chickenstats.utilities import ChickenProgress
from chickenstats.utilities.utilities import COLLECT_ENGINE, _to_polars, _detect_backend, _to_backend, _validate_backend

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

    from chickenstats.utilities.types import (
        DataFrameT,
        InputFrameT,
        NarwhalsBackend,
        NarwhalsFrame,
        PandasBackend,
        PolarsBackend,
        PyarrowBackend,
    )


def _munge_rosters(raw_shifts: pl.DataFrame) -> pl.DataFrame:
    """Prepares rosters from a csv file of evolving-hockey.com shifts data for use in the `prep_pbp` function.

    Parameters:
        raw_shifts (pl.DataFrame):
            Polars dataframe of shifts data available from the queries section of evolving-hockey.com
            (https://evolving-hockey.com/stats/shifts_query/). Subscription required.
    """
    keep_columns = ["game_id", "season", "session", "team", "player", "team_num", "position"]

    return (
        raw_shifts.select(keep_columns)
        .unique(maintain_order=True)
        .rename({"team_num": "team_jersey"})
        .with_columns(
            pl.col("team").replace(TEAM_REPLACE),
            pl.col("team_jersey").str.replace_many(list(TEAM_REPLACE), list(TEAM_REPLACE.values())),
        )
        .with_columns(
            name_key_expr(pl.col("player")).alias("name_key"),
            eh_id_expr(pl.col("player")).alias("eh_id"),
            player_name_expr(pl.col("player")).alias("player"),
        )
    )


def _munge_pbp(raw_pbp: pl.DataFrame) -> pl.DataFrame:
    """Prepares csv file of evolving-hockey.com play-by-play data for use in the `prep_pbp` function.

    Parameters:
        raw_pbp (pl.DataFrame):
            Polars dataframe of pbp data available from the queries section of evolving-hockey.com
            (https://evolving-hockey.com/stats/pbp_query/). Subscription required.

    """
    event_team_is_home = pl.col("event_team") == pl.col("home_team")
    event_team_is_away = pl.col("event_team") == pl.col("away_team")

    def by_side(home: pl.Expr, away: pl.Expr):
        """Pick the home or away value by the event team, null when the event has no team."""
        return pl.when(event_team_is_home).then(home).when(event_team_is_away).then(away)

    # pandas reads a column with no values as numbers, which is any seventh on-ice slot in a single game
    string_columns_expr = (
        cs.contains("_team", "_on_", "event_player_", "_goalie")
        | cs.by_name("players_on", "players_off", "event_description", "event_detail", "event_zone", "home_zone")
    ).cast(pl.String)

    # Fixing event teams in a few different columns
    old_teams = list(TEAM_REPLACE.keys())
    new_teams = list(TEAM_REPLACE.values())

    replace_teams_expr = (
        (cs.contains("_team") | cs.by_name("players_on", "players_off", "event_description"))
        .str.strip_chars()
        .replace({"": None, " ": None})
        .str.replace_many(old_teams, new_teams)
    )

    # Creating the opposing team column
    opp_team_expr = by_side(pl.col("away_team"), pl.col("home_team")).alias("opp_team")

    # Creating the players on for the event team and the opposition team
    event_on_exprs = [
        by_side(pl.col(f"home_on_{x}"), pl.col(f"away_on_{x}")).alias(f"event_on_{x}") for x in range(1, 8)
    ]
    opp_on_exprs = [by_side(pl.col(f"away_on_{x}"), pl.col(f"home_on_{x}")).alias(f"opp_on_{x}") for x in range(1, 8)]

    # Creating the zone start column
    next_fac_zone_expr = (
        pl.when(pl.col("event_type") == "FAC")
        .then(pl.col("home_zone").str.to_uppercase())
        .fill_null(strategy="backward")
        .over(["game_id", "game_period", "game_seconds"])
    )

    zone_start_expr = (
        pl.when(pl.col("event_type") == "CHANGE")
        .then(
            pl.when(event_team_is_away & (next_fac_zone_expr == "OFF"))
            .then(pl.lit("DEF"))
            .when(event_team_is_away & (next_fac_zone_expr == "DEF"))
            .then(pl.lit("OFF"))
            .when(next_fac_zone_expr.is_null())
            .then(pl.lit("OTF"))
            .otherwise(next_fac_zone_expr)
        )
        .alias("zone_start")
    )

    event_zone_expr = pl.col("event_zone").str.to_uppercase()

    # Creating the proper strength state columns, adjusting for weird changes logic
    next_fac_strength_expr = (
        pl.when(pl.col("event_type") == "FAC")
        .then(pl.col("game_strength_state"))
        .otherwise(None)
        .fill_null(strategy="backward")
        .over(["game_id", "game_period", "game_seconds"])
    )

    adjusted_strength_expr = (
        pl.when(pl.col("event_type") == "CHANGE")
        .then(
            pl.when(next_fac_strength_expr.is_not_null())
            .then(next_fac_strength_expr)
            .otherwise(pl.col("game_strength_state"))
        )
        .otherwise(pl.col("game_strength_state"))
    )

    strength_state_split = adjusted_strength_expr.str.split("v")
    flipped_strength_expr = (
        strength_state_split.list.get(1, null_on_oob=True) + "v" + strength_state_split.list.get(0, null_on_oob=True)
    )

    is_illegal = adjusted_strength_expr == "illegal"
    strength_state_expr = (
        pl.when(is_illegal)
        .then(pl.lit("illegal"))
        .otherwise(by_side(adjusted_strength_expr, flipped_strength_expr))
        .alias("strength_state")
    )
    opp_strength_state_expr = (
        pl.when(is_illegal)
        .then(pl.lit("illegal"))
        .otherwise(by_side(flipped_strength_expr, adjusted_strength_expr))
        .alias("opp_strength_state")
    )

    # Creating score state column
    score_state_split = pl.col("game_score_state").str.split("v")
    flipped_score_state = score_state_split.list.get(1) + "v" + score_state_split.list.get(0)

    score_state_expr = (
        by_side(pl.col("game_score_state"), flipped_score_state).otherwise("game_score_state").alias("score_state")
    )
    opp_score_state_expr = (
        by_side(flipped_score_state, pl.col("game_score_state")).otherwise(flipped_score_state).alias("opp_score_state")
    )

    # Swapping players to account for who won / lost the faceoff
    home_won_faceoff = event_team_is_home & (pl.col("event_type") == "FAC")
    player_1_fac_expr = (
        pl.when(home_won_faceoff).then("event_player_2").otherwise("event_player_1").alias("event_player_1")
    )
    player_2_fac_expr = (
        pl.when(home_won_faceoff).then("event_player_1").otherwise("event_player_2").alias("event_player_2")
    )

    # Creating is_home dummy column
    is_home_expr = (
        pl.when(event_team_is_home).then(pl.lit(1, dtype=pl.Int8)).otherwise(pl.lit(0, dtype=pl.Int8)).alias("is_home")
    )

    # Creating event_type dummy columns
    event_types = [
        "CHL",
        "DELPEN",
        "GOAL",
        "MISS",
        "STOP",
        "FAC",
        "GIVE",
        "SHOT",
        "TAKE",
        "BLOCK",
        "HIT",
        "CHANGE",
        "PENL",
    ]

    dummy_event_types_exprs = [
        (pl.col("event_type") == event_type).cast(pl.Int8).alias(event_type.lower()) for event_type in event_types
    ]

    # Creating dummy columns for the faceoff zones
    fac_exprs = [
        ((pl.col("event_type") == "FAC") & (pl.col("event_zone") == "DEF")).cast(pl.Int8).alias("dzf"),
        ((pl.col("event_type") == "FAC") & (pl.col("event_zone") == "NEU")).cast(pl.Int8).alias("nzf"),
        ((pl.col("event_type") == "FAC") & (pl.col("event_zone") == "OFF")).cast(pl.Int8).alias("ozf"),
    ]

    # Creating dummy columns for the change zones
    change_exprs = [
        ((pl.col("event_type") == "CHANGE") & (pl.col("zone_start") == "DEF")).cast(pl.Int8).alias("dzs"),
        ((pl.col("event_type") == "CHANGE") & (pl.col("zone_start") == "NEU")).cast(pl.Int8).alias("nzs"),
        ((pl.col("event_type") == "CHANGE") & (pl.col("zone_start") == "OFF")).cast(pl.Int8).alias("ozs"),
        ((pl.col("event_type") == "CHANGE") & (pl.col("zone_start") == "OTF")).cast(pl.Int8).alias("otf"),
    ]

    # A shootout attempt counts for none of the shot columns, only for its own two
    is_shootout = (pl.col("game_period") == 5) & (pl.col("session") == "R")
    is_attempt = pl.col("event_type").is_in(FENWICK_EVENTS)

    shootout_exprs = [
        (is_shootout & is_attempt).cast(pl.Int8).alias("shootout_attempt"),
        (is_shootout & (pl.col("event_type") == "GOAL")).cast(pl.Int8).alias("shootout_goal"),
    ]

    clear_shootout_exprs = [
        *[pl.when(is_shootout).then(pl.lit(0, dtype=pl.Int8)).otherwise(x).alias(x) for x in ["goal", "shot", "miss"]],
        pl.when(~is_shootout).then("pred_goal").alias("pred_goal"),
    ]

    # A blocked attempt that hit a teammate is still a blocked attempt, and has no blocker to credit
    teammate_block_expr = (
        ((pl.col("event_type") == "BLOCK") & pl.col("event_description").str.contains("(?i)BLOCKED BY TEAMMATE"))
        .fill_null(False)
        .cast(pl.Int8)
        .alias("teammate_block")
    )

    # Updating shot column to include goals
    shot_expr = (pl.col("shot").cast(pl.Int8) + pl.col("goal").cast(pl.Int8)).alias("shot")

    # Creating fenwick column
    fenwick_expr = (pl.col("shot") + pl.col("miss")).alias("fenwick")

    # Creating corsi column
    corsi_expr = (pl.col("shot") + pl.col("miss") + pl.col("block")).alias("corsi")

    # Creating the penalty dummies and penalty type columns
    penalty_mapping = {"0min": "pen0", "2min": "pen2", "4min": "pen4", "5min": "pen5", "10min": "pen10"}

    dummy_penalties_exprs = [
        ((pl.col("event_type") == "PENL") & (pl.col("event_detail") == original_penalty))
        .cast(pl.Int8)
        .alias(new_col_name)
        for original_penalty, new_col_name in penalty_mapping.items()
    ]

    # Editing game periods and game seconds
    game_periods_and_seconds_expr = pl.col(["game_period", "game_seconds"]).fill_null(0)

    # Creating period seconds column
    period_seconds_expr = (
        pl.when((pl.col("game_period") == 5) & (pl.col("session") == "R"))
        .then(pl.lit(0))
        .otherwise(pl.col("game_seconds") - ((pl.col("game_period") - 1) * 1200))
        .fill_null(0)
        .alias("period_seconds")
    )

    # Creating the ID column
    id_expr = (
        (pl.col("game_id").cast(pl.String) + pl.col("event_index").cast(pl.String).str.zfill(4))
        .cast(pl.Int64)
        .alias("id")
    )

    # Calculating danger and high-danger shots
    abs_x = pl.col("coords_x").abs()
    abs_y = pl.col("coords_y").abs()

    high_danger_geom = (abs_x.is_between(69, 89)) & (abs_y <= 9)

    danger_geom = (
        (abs_x.is_between(44, 54) & (abs_y <= 9))
        | (abs_x.is_between(54, 69) & (abs_y <= 22))
        | (abs_x.is_between(69, 89) & (abs_y <= -0.65 * abs_x + 66.85))  # The diagonal boundary
    )

    is_valid_shot = (pl.col("event_zone") == "OFF") & pl.col("event_type").is_in(FENWICK_EVENTS)

    spatial_exprs = [
        (is_valid_shot & high_danger_geom).cast(pl.Int8).alias("high_danger"),
        (is_valid_shot & danger_geom & ~high_danger_geom).cast(pl.Int8).alias("danger"),
    ]

    # Calculate the HD variants
    hd_exprs = [(pl.col("high_danger") * pl.col(x)).alias(f"hd_{x}") for x in ["goal", "shot", "miss", "fenwick"]]

    # The home score difference, capped as in the score-adjustment table
    score_diff = pl.col("home_score").cast(pl.Int64) - pl.col("away_score").cast(pl.Int64)
    score_bucket_expr = score_diff.clip(-3, 3).cast(pl.Int8).alias("score_bucket")

    return (
        raw_pbp.lazy()
        # Pass 1: the team codes, which everything below compares and copies
        .with_columns(string_columns_expr)
        .with_columns(replace_teams_expr)
        # Pass 2: all expressions that depend only on original columns
        .with_columns(
            id_expr,
            player_1_fac_expr,
            player_2_fac_expr,
            game_periods_and_seconds_expr,
            period_seconds_expr,
            opp_team_expr,
            *event_on_exprs,
            *opp_on_exprs,
            event_zone_expr,
            zone_start_expr,
            strength_state_expr,
            opp_strength_state_expr,
            score_state_expr,
            opp_score_state_expr,
            is_home_expr,
            *dummy_event_types_exprs,
            *dummy_penalties_exprs,
            *shootout_exprs,
            teammate_block_expr,
        )
        .with_columns(clear_shootout_exprs)
        # Pass 3: shot update, fac/change dummies, spatial, score_bucket
        # (spatial_exprs needs the pass 2 event_zone)
        .with_columns(shot_expr, *fac_exprs, *change_exprs, *spatial_exprs, score_bucket_expr)
        # Pass 4: fenwick + corsi (need updated shot from pass 3)
        .with_columns(fenwick_expr, corsi_expr)
        # Join replaces 5×72 nested when/then/otherwise chains
        .join(_weights.get_adj_weights_lf(), on=["strength_state", "is_home", "score_bucket"], how="left")
        # Pass 5: hd_exprs + adjusted stats (both need fenwick/high_danger from pass 4).
        # A state with no weights, such as a penalty shot or an empty net, keeps its raw value, as in chicken_nhl
        .with_columns(
            *hd_exprs,
            (pl.col("goal") * pl.col("goal_w").fill_null(1.0)).alias("goal_adj"),
            (pl.col("pred_goal") * pl.col("xg_w").fill_null(1.0)).alias("pred_goal_adj"),
            (pl.col("shot") * pl.col("shot_w").fill_null(1.0)).alias("shot_adj"),
            (pl.col("miss") * pl.col("fenwick_w").fill_null(1.0)).alias("miss_adj"),
            (pl.col("fenwick") * pl.col("fenwick_w").fill_null(1.0)).alias("fenwick_adj"),
            (pl.col("block") * pl.col("corsi_w").fill_null(1.0)).alias("block_adj"),
            (pl.col("teammate_block") * pl.col("corsi_w").fill_null(1.0)).alias("teammate_block_adj"),
            (pl.col("corsi") * pl.col("corsi_w").fill_null(1.0)).alias("corsi_adj"),
        )
        .drop(["score_bucket", "goal_w", "xg_w", "shot_w", "fenwick_w", "corsi_w"])
        .collect(engine=COLLECT_ENGINE)
    )


def _join_player(pbp: pl.DataFrame, rosters: pl.DataFrame, column: str, team: pl.Expr) -> pl.DataFrame:
    """Adds the eh_id and position of the player in a column, and writes his name as chicken_nhl does.

    Two players can share a name, so a player is found on his own team.
    """
    joined = (
        pbp.with_columns(team.alias("__team"), name_key_expr(pl.col(column)).alias("__key"))
        .join(rosters, left_on=["game_id", "__team", "__key"], right_on=["game_id", "team", "name_key"], how="left")
        .drop(["__team", "__key"])
    )

    return (
        joined.rename({"eh_id": f"{column}_eh_id", "position": f"{column}_pos"})
        .with_columns(pl.coalesce("player", player_name_expr(pl.col(column))).alias(column))
        .drop("player")
    )


def _add_positions(pbp: pl.DataFrame, rosters: pl.DataFrame) -> pl.DataFrame:
    """Adds position data to the play-by-play data from evolving-hockey.com."""
    lookup = rosters.select(["game_id", "team", "name_key", "player", "eh_id", "position"]).unique(
        subset=["game_id", "team", "name_key"], maintain_order=True
    )

    # player_2 is on the other team when he takes a hit, loses a faceoff, blocks a shot or draws a penalty
    player_2_team = (
        pl.when(pl.col("event_type").is_in(OPPOSING_PLAYER_2_EVENTS))
        .then(pl.col("opp_team"))
        .otherwise(pl.col("event_team"))
    )

    player_teams = {
        "event_player_1": pl.col("event_team"),
        "event_player_2": player_2_team,
        "event_player_3": pl.col("event_team"),
        **{f"event_on_{x}": pl.col("event_team") for x in range(1, 8)},
        **{f"opp_on_{x}": pl.col("opp_team") for x in range(1, 8)},
    }

    for column, team in player_teams.items():
        pbp = _join_player(pbp, lookup, column, team)

    # On a penalty shot or in a shootout, only the shooter and the defending goalie are on the ice
    shooter_alone = (pl.col("strength_state") == "1v0") | (
        (pl.col("session") == "R") & (pl.col("period") == 5) & pl.col("strength_state").is_not_null()
    )

    pbp = pbp.with_columns(
        pl.when(shooter_alone & (pl.col(f"event_on_{x}_pos") == "G")).then(None).otherwise(pl.col(column)).alias(column)
        for x in range(1, 8)
        for column in (f"event_on_{x}", f"event_on_{x}_eh_id", f"event_on_{x}_pos")
    )

    # Rebuild players_on/players_off with names, eh_ids, and positions
    pbp = pbp.with_row_index("__row")
    jerseys = rosters.select(["game_id", "team_jersey", "player", "eh_id", "position"]).unique(
        subset=["game_id", "team_jersey"], maintain_order=True
    )

    for target_col in ["players_on", "players_off"]:
        rebuilt = (
            pbp.select(["__row", "game_id", pl.col(target_col).str.split(", ").alias("team_jersey")])
            .explode("team_jersey", empty_as_null=True)
            .filter(pl.col("team_jersey").is_not_null() & (pl.col("team_jersey") != ""))
            .join(jerseys, on=["game_id", "team_jersey"], how="inner", maintain_order="left")
            .group_by("__row", maintain_order=True)
            .agg(
                pl.col("player").str.join(", ").alias(target_col),
                pl.col("eh_id").str.join(", ").alias(f"{target_col}_eh_id"),
                pl.col("position").str.join(", ").alias(f"{target_col}_pos"),
            )
        )

        pbp = pbp.drop(target_col).join(rebuilt, on="__row", how="left", maintain_order="left")

    # Aggregate players into position groups
    positions = {"f": ["L", "C", "R"], "d": ["D"], "g": ["G"]}

    # Maps (player_group, pos_group) → (name_col, eh_id_col) for final output names
    composite_col_names = {
        ("event", "f"): ("forwards", "forwards_eh_id"),
        ("event", "d"): ("defense", "defense_eh_id"),
        ("event", "g"): ("own_goalie", "own_goalie_eh_id"),
        ("opp", "f"): ("opp_forwards", "opp_forwards_eh_id"),
        ("opp", "d"): ("opp_defense", "opp_defense_eh_id"),
        ("opp", "g"): ("opp_goalie", "opp_goalie_eh_id"),
    }

    for player_group in ["event", "opp"]:
        stacked = pl.concat(
            pbp.select(
                "__row",
                pl.col(f"{player_group}_on_{x}").alias("name"),
                pl.col(f"{player_group}_on_{x}_pos").alias("pos"),
                pl.col(f"{player_group}_on_{x}_eh_id").alias("id"),
            )
            for x in range(1, 8)
        )

        agg_exprs = []
        for pos_group, group_positions in positions.items():
            pos_filter = pl.col("pos").is_in(group_positions)
            name_col, id_col = composite_col_names[(player_group, pos_group)]
            agg_exprs += [
                pl.col("name").filter(pos_filter).str.join(", ").alias(name_col),
                pl.col("id").filter(pos_filter).str.join(", ").alias(id_col),
            ]

        # Sorted by name first, so the ids stay in the same order as the names
        aggregated = stacked.filter(pl.col("name").is_not_null()).sort("name").group_by("__row").agg(agg_exprs)

        # A group with nobody in it is null, not an empty string
        pbp = pbp.join(aggregated, on="__row", how="left", maintain_order="left").with_columns(
            pl.col(column).replace("", None)
            for pair in composite_col_names.values()
            for column in pair
            if column in aggregated.columns
        )

    return pbp.drop("__row")


@overload
def prep_pbp(
    pbp: InputFrameT | list[InputFrameT],
    shifts: DataFrameT | list[DataFrameT],
    *,
    columns: Literal["light", "full", "all"] = "full",
    disable_progress_bar: bool = False,
    backend: None = None,
) -> InputFrameT: ...
@overload
def prep_pbp(
    pbp: DataFrameT | list[DataFrameT],
    shifts: DataFrameT | list[DataFrameT],
    *,
    columns: Literal["light", "full", "all"] = "full",
    disable_progress_bar: bool = False,
    backend: PolarsBackend,
) -> pl.DataFrame: ...
@overload
def prep_pbp(
    pbp: DataFrameT | list[DataFrameT],
    shifts: DataFrameT | list[DataFrameT],
    *,
    columns: Literal["light", "full", "all"] = "full",
    disable_progress_bar: bool = False,
    backend: PandasBackend,
) -> pd.DataFrame: ...
@overload
def prep_pbp(
    pbp: DataFrameT | list[DataFrameT],
    shifts: DataFrameT | list[DataFrameT],
    *,
    columns: Literal["light", "full", "all"] = "full",
    disable_progress_bar: bool = False,
    backend: PyarrowBackend,
) -> pa.Table: ...
@overload
def prep_pbp(
    pbp: DataFrameT | list[DataFrameT],
    shifts: DataFrameT | list[DataFrameT],
    *,
    columns: Literal["light", "full", "all"] = "full",
    disable_progress_bar: bool = False,
    backend: NarwhalsBackend,
) -> NarwhalsFrame: ...
@overload
def prep_pbp(
    pbp: DataFrameT | list[DataFrameT],
    shifts: DataFrameT | list[DataFrameT],
    *,
    columns: Literal["light", "full", "all"] = "full",
    disable_progress_bar: bool = False,
    backend: str | None = None,
) -> Any: ...
def prep_pbp(
    pbp: DataFrameT | list[DataFrameT],
    shifts: DataFrameT | list[DataFrameT],
    *,
    columns: Literal["light", "full", "all"] = "full",
    disable_progress_bar: bool = False,
    backend: str | None = None,
) -> Any:
    """Prepares a play-by-play dataframe using evolving-hockey.com data, adding stats and position info.

    Accepts any narwhals-compatible DataFrame (Polars, pandas, etc.) for both ``pbp`` and ``shifts``.
    Internally converts to Polars, processes, validates, and returns in the requested backend.

    Player names and team codes match chicken_nhl, apart from the first names the exports shorten. The lineup
    columns are ordered by player name, where chicken_nhl orders them by NHL API id, which the exports do not have.

    Parameters:
        pbp:
            DataFrame (or list of DataFrames) from the play-by-play query at evolving-hockey.com.
        shifts:
            DataFrame (or list of DataFrames) from the shifts query at evolving-hockey.com.
            Must be the same length as ``pbp``.
        columns:
            Controls which columns are returned.
            ``"light"`` returns the core set. ``"full"`` additionally includes individual
            on-ice player slots (event_on_1..7, opp_on_1..7) and opposing state columns.
            ``"all"`` further adds raw home/away game columns from the source CSV.
        disable_progress_bar:
            Set to ``True`` to suppress the progress bar.
        backend:
            Output backend. One of ``"polars"``, ``"pandas"``, or ``"pyarrow"``.
            Defaults to the backend of the first ``pbp`` input.

    Returns:
        DataFrame in the requested backend with processed play-by-play data.

    Examples:
        >>> import polars as pl
        >>> from chickenstats.evolving_hockey.pbp import prep_pbp
        >>> pbp = prep_pbp(pl.read_csv("raw_pbp.csv"), pl.read_csv("raw_shifts.csv"))
    """
    if columns not in ("light", "full", "all"):
        raise InvalidInputError(f"columns must be 'light', 'full' or 'all', got {columns!r}", obj=columns)

    first = pbp[0] if isinstance(pbp, list) else pbp
    backend = _validate_backend(backend or _detect_backend(first))

    if not isinstance(pbp, list):
        pbp = [pbp]
    if not isinstance(shifts, list):
        shifts = [shifts]

    if len(pbp) != len(shifts):
        raise DataMismatchError("Number of play-by-play and shift CSV files does not match")

    # Base column list ("light" mode)
    base_cols = [
        "id",
        "season",
        "session",
        "game_id",
        "game_date",
        "event_index",
        "period",
        "game_seconds",
        "period_seconds",
        "clock_time",
        "strength_state",
        "score_state",
        "event_type",
        "event_description",
        "event_detail",
        "event_zone",
        "event_team",
        "opp_team",
        "is_home",
        "coords_x",
        "coords_y",
        "event_player_1",
        "event_player_1_eh_id",
        "event_player_1_pos",
        "event_player_2",
        "event_player_2_eh_id",
        "event_player_2_pos",
        "event_player_3",
        "event_player_3_eh_id",
        "event_player_3_pos",
        "event_length",
        "high_danger",
        "danger",
        "pbp_distance",
        "event_distance",
        "event_angle",
        "forwards",
        "forwards_eh_id",
        "defense",
        "defense_eh_id",
        "own_goalie",
        "own_goalie_eh_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_goalie",
        "opp_goalie_eh_id",
        "change",
        "zone_start",
        "num_on",
        "num_off",
        "players_on",
        "players_on_eh_id",
        "players_on_pos",
        "players_off",
        "players_off_eh_id",
        "players_off_pos",
        "shot",
        "shot_adj",
        "goal",
        "goal_adj",
        "pred_goal",
        "pred_goal_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "corsi",
        "corsi_adj",
        "fenwick",
        "fenwick_adj",
        "shootout_attempt",
        "shootout_goal",
        "teammate_block",
        "teammate_block_adj",
        "hd_shot",
        "hd_goal",
        "hd_miss",
        "hd_fenwick",
        "fac",
        "hit",
        "give",
        "take",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
        "stop",
        "ozf",
        "nzf",
        "dzf",
        "ozs",
        "nzs",
        "dzs",
        "otf",
    ]

    results = []

    with ChickenProgress(disable=disable_progress_bar) as progress:
        task = progress.add_task("Prepping play-by-play data...", total=len(pbp))

        for idx, (pbp_raw, shifts_raw) in enumerate(zip(pbp, shifts, strict=False)):
            rosters = _munge_rosters(_to_polars(shifts_raw))
            pbp_clean = _munge_pbp(_to_polars(pbp_raw))
            pbp_clean = pbp_clean.rename({"game_period": "period"})
            pbp_clean = _add_positions(pbp_clean, rosters)

            cols = list(base_cols)

            if columns in ["full", "all"]:
                # Insert individual on-ice player slots after the position-group summary columns
                event_on_cols = [
                    x for i in range(1, 8) for x in (f"event_on_{i}", f"event_on_{i}_eh_id", f"event_on_{i}_pos")
                ]
                opp_on_cols = [x for i in range(1, 8) for x in (f"opp_on_{i}", f"opp_on_{i}_eh_id", f"opp_on_{i}_pos")]

                event_pos = cols.index("own_goalie_eh_id") + 1
                cols[event_pos:event_pos] = event_on_cols

                opp_pos = cols.index("opp_goalie_eh_id") + 1
                cols[opp_pos:opp_pos] = opp_on_cols

                # Insert opposing state columns after event_angle
                other_pos = cols.index("event_angle") + 1
                cols[other_pos:other_pos] = ["opp_strength_state", "opp_score_state"]

            if columns == "all":
                # Insert raw home/away game columns after is_home
                raw_cols = [
                    "home_zone",
                    "home_team",
                    "away_team",
                    "home_goalie",
                    "away_goalie",
                    "home_skaters",
                    "away_skaters",
                    "home_score",
                    "away_score",
                    "home_zonestart",
                    "face_index",
                    "pen_index",
                    "shift_index",
                    "game_score_state",
                    "game_strength_state",
                ]
                raw_pos = cols.index("is_home") + 1
                cols[raw_pos:raw_pos] = raw_cols

            # Keep only columns that exist in the processed DataFrame
            cols = [c for c in cols if c in pbp_clean.columns]
            pbp_clean = pbp_clean.select(cols)

            results.append(pbp_clean)

            description = (
                "Finished loading play-by-play data" if idx + 1 == len(pbp) else "Prepping play-by-play data..."
            )
            progress.update(task, description=description, advance=1, refresh=True)

    result = pl.concat(results, how="diagonal_relaxed")
    result = result.select([c for c in PBPSchema.columns if c in result.columns])
    result = coerce_to_schema(result, PBPSchema)
    return _to_backend(result, backend)
