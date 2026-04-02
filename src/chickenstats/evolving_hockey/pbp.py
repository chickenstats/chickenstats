from typing import Literal, cast

import narwhals as nw
import polars as pl
import polars.selectors as cs

from chickenstats.evolving_hockey import _weights
from chickenstats.exceptions import DataMismatchError
from chickenstats.utilities import ChickenProgress

# Duplicate names to replaced with f"{name}2"
duplicate_names = {
    "SEBASTIAN.AHO": pl.col("position") == "D",
    "COLIN.WHITE": pl.col("season") >= 20162017,
    "SEAN.COLLINS": (pl.col("position").is_not_null() & (pl.col("position") != "D")),
    "ALEX.PICARD": (pl.col("position").is_not_null() & (pl.col("position") != "D")),
    "ERIK.GUSTAFSSON": pl.col("season") >= 20152016,
    "MIKKO.LEHTONEN": pl.col("season") >= 20202021,
    "NATHAN.SMITH": pl.col("season") >= 20212022,
    "DANIIL.TARASOV": pl.col("position") == "G",
    "ELIAS.PETTERSSON": ((pl.col("position") == "D") | (pl.col("team_jersey") == "VAN25")),
}

# Names to shorten
shortened_names = {"ALEXANDER": "ALEX", "ALEXANDRE": "ALEX", "CHRISTOPHER": "CHRIS"}

# teams to replace
replacement_teams = {"S.J": "SJS", "N.J": "NJD", "T.B": "TBL", "L.A": "LAK"}


def _normalize_name_expr(expr: pl.Expr) -> pl.Expr:
    """Applies NFKD normalization, diacritic removal, and name shortening to a Polars string expression."""
    return (
        expr.str.normalize("NFKD")
        .str.replace_all(r"\p{Mn}", "")
        .str.replace_many(list(shortened_names.keys()), list(shortened_names.values()))
    )


def build_adjustment_expr(conditions, weights, base_col, output_name):
    """Dynamically builds the expression for adjusted goals, fenwick, etc."""
    expr = pl.lit(0.0)

    for cond, weight in reversed(list(zip(conditions, weights, strict=True))):
        expr = pl.when(cond).then(pl.col(base_col) * weight).otherwise(expr)

    return expr.alias(output_name)


def munge_rosters(raw_shifts: pl.DataFrame | pl.LazyFrame) -> pl.DataFrame | pl.LazyFrame:
    """Prepares csv file of shifts data for use in the `prep_pbp` function.

    Parameters:
        raw_shifts (pl.DataFrame):
            Polars dataframe of shifts data available from the queries section of evolving-hockey.com
            (https://evolving-hockey.com/stats/shifts_query/). Subscription required.
    """
    lf: pl.LazyFrame = raw_shifts.lazy()

    keep_columns = ["game_id", "season", "session", "team", "player", "team_num", "position"]

    eh_id = _normalize_name_expr(pl.col("player"))

    for name, conditions in duplicate_names.items():
        eh_id = pl.when((eh_id == name) & conditions).then(eh_id + "2").otherwise(eh_id)

    rosters = (
        lf.select(keep_columns)
        .unique()
        .rename({"team_num": "team_jersey"})
        .with_columns(eh_id.alias("eh_id"), pl.col("team").replace(replacement_teams))
    )

    return cast(pl.DataFrame, rosters.collect()) if isinstance(raw_shifts, pl.DataFrame) else rosters


def munge_pbp(raw_pbp: pl.DataFrame) -> pl.DataFrame:
    """Prepares csv file of play-by-play data for use in the `prep_pbp` function.

    Parameters:
        raw_pbp (pl.DataFrame):
            Polars dataframe of pbp data available from the queries section of evolving-hockey.com
            (https://evolving-hockey.com/stats/pbp_query/). Subscription required.

    """
    event_team_is_home = pl.col("event_team") == pl.col("home_team")
    event_team_is_away = pl.col("event_team") == pl.col("away_team")

    # Fixing event teams in a few different columns
    old_teams = list(replacement_teams.keys())
    new_teams = list(replacement_teams.values())

    replace_teams_expr = (
        (cs.contains("_team") | cs.by_name("players_on", "players_off", "event_description"))
        .str.strip_chars()
        .replace({"": None, " ": None})
        .str.replace_many(old_teams, new_teams)
    )

    # Creating the opposing team column
    opp_team_expr = (
        pl.when(event_team_is_home)
        .then("away_team")
        .when(event_team_is_away)
        .then("home_team")
        .otherwise(pl.lit(None))
        .alias("opp_team")
    )

    # Creating the opposing goalie column
    opp_goalie_expr = _normalize_name_expr(
        pl.when(event_team_is_home)
        .then("away_goalie")
        .when(event_team_is_away)
        .then("home_goalie")
        .otherwise(pl.lit(None))
    ).alias("opp_goalie")

    # Creating the own goalie column
    own_goalie_expr = _normalize_name_expr(
        pl.when(event_team_is_home)
        .then("home_goalie")
        .when(event_team_is_away)
        .then("away_goalie")
        .otherwise(pl.lit(None))
    ).alias("own_goalie")

    # Creating the players on for the event team
    event_on_exprs = [
        _normalize_name_expr(
            pl.when(event_team_is_home)
            .then(pl.col(f"home_on_{x}"))
            .when(event_team_is_away)
            .then(pl.col(f"away_on_{x}"))
            .otherwise(pl.lit(None))
        ).alias(f"event_on_{x}")
        for x in range(1, 8)
    ]

    # Creating the players on for the opposition team
    opp_on_exprs = [
        _normalize_name_expr(
            pl.when(event_team_is_home)
            .then(pl.col(f"away_on_{x}"))
            .when(event_team_is_away)
            .then(pl.col(f"home_on_{x}"))
            .otherwise(pl.lit(None))
        ).alias(f"opp_on_{x}")
        for x in range(1, 8)
    ]

    # Creating the zone start column
    next_fac_zone_expr = (
        pl.when(pl.col("event_type") == "FAC")
        .then(pl.col("home_zone").str.to_uppercase())
        .otherwise(pl.lit(None))
        .fill_null(strategy="backward")
        .over(["game_period", "game_seconds"])
    )

    zone_start_expr = (
        pl.when(pl.col("event_type") == "CHANGE")
        .then(
            pl.when(event_team_is_away & (next_fac_zone_expr == "Off"))
            .then(pl.lit("DEF"))
            .when(event_team_is_away & (next_fac_zone_expr == "Def"))
            .then(pl.lit("OFF"))
            .when(next_fac_zone_expr.is_null())
            .then(pl.lit("OTF"))
            .otherwise(next_fac_zone_expr)
        )
        .otherwise(pl.lit(None))
        .alias("zone_start")
    )

    event_zone_expr = pl.col("event_zone").str.to_uppercase()

    # Creating the proper strength state columns, adjusting for weird changes logic
    next_fac_strength_expr = (
        pl.when(pl.col("event_type") == "FAC")
        .then(pl.col("game_strength_state"))
        .otherwise(None)
        .fill_null(strategy="backward")
        .over(["game_period", "game_seconds"])
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
    flipped_strength_expr = strength_state_split.list.get(1) + "v" + strength_state_split.list.get(0)

    strength_state_expr = (
        pl.when(adjusted_strength_expr == "illegal")
        .then(pl.lit("illegal"))
        .when(event_team_is_home)
        .then(adjusted_strength_expr)
        .when(event_team_is_away)
        .then(flipped_strength_expr)
        .otherwise(pl.lit(None))
        .alias("strength_state")
    )

    opp_strength_state_expr = (
        pl.when(adjusted_strength_expr == "illegal")
        .then(pl.lit("illegal"))
        .when(event_team_is_home)
        .then(flipped_strength_expr)
        .when(event_team_is_away)
        .then(adjusted_strength_expr)
        .otherwise(pl.lit(None))
        .alias("opp_strength_state")
    )

    # Creating score state column
    score_state_split = pl.col("game_score_state").str.split("v")
    flipped_score_state = score_state_split.list.get(1) + "v" + score_state_split.list.get(0)

    score_state_expr = (
        pl.when(event_team_is_home)
        .then(pl.col("game_score_state"))
        .when(event_team_is_away)
        .then(flipped_score_state)
        .otherwise("game_score_state")
        .alias("score_state")
    )
    opp_score_state_expr = (
        pl.when(event_team_is_home)
        .then(flipped_score_state)
        .when(event_team_is_away)
        .then(pl.col("game_score_state"))
        .otherwise(flipped_score_state)
        .alias("opp_score_state")
    )

    # Swapping players to account for who won / lost the faceoff
    player_1_fac_expr = (
        pl.when(event_team_is_home & (pl.col("event_type") == "FAC")).then("event_player_2").otherwise("event_player_1")
    )
    player_2_fac_expr = (
        pl.when(event_team_is_home & (pl.col("event_type") == "FAC")).then("event_player_1").otherwise("event_player_2")
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

    # Creaing the ID column
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

    is_valid_shot = (pl.col("event_zone") == "OFF") & pl.col("event_type").is_in(["GOAL", "SHOT", "MISS"])

    spatial_exprs = [
        (is_valid_shot & high_danger_geom).cast(pl.Int8).alias("high_danger"),
        (is_valid_shot & danger_geom & ~high_danger_geom).cast(pl.Int8).alias("danger"),
    ]

    # Calculate the HD variants
    hd_exprs = [(pl.col("high_danger") * pl.col(x)).alias(f"hd_{x}") for x in ["goal", "shot", "miss", "fenwick"]]

    # Score bucket for lookup join: 7 buckets for 5v5/4v4, 1 for 3v3, 3 for all others
    score_diff = pl.col("home_score").cast(pl.Int64) - pl.col("away_score").cast(pl.Int64)
    score_bucket_expr = (
        pl.when(pl.col("strength_state").is_in(["5v5", "4v4"]))
        .then(score_diff.clip(-3, 3))
        .when(pl.col("strength_state") == "3v3")
        .then(pl.lit(0))
        .otherwise(score_diff.sign())
        .cast(pl.Int8)
        .alias("score_bucket")
    )

    return cast(
        pl.DataFrame,
        (
            raw_pbp.lazy()
            # Pass 1: all expressions that depend only on original columns
            .with_columns(
                id_expr,
                replace_teams_expr,
                player_1_fac_expr,
                player_2_fac_expr,
                game_periods_and_seconds_expr,
                period_seconds_expr,
                opp_team_expr,
                opp_goalie_expr,
                own_goalie_expr,
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
            )
            # Pass 2: shot update, fac/change dummies, spatial, score_bucket
            # (spatial_exprs needs pass-1 event_zone; score_bucket needs pass-1 strength_state)
            .with_columns(shot_expr, *fac_exprs, *change_exprs, *spatial_exprs, score_bucket_expr)
            # Pass 3: fenwick + corsi (need updated shot from pass 2)
            .with_columns(fenwick_expr, corsi_expr)
            # Join: O(n) hash join replaces 5×72 nested when/then/otherwise chains
            .join(_weights.adj_weights_lf, on=["strength_state", "is_home", "score_bucket"], how="left")
            # Pass 4: hd_exprs + adjusted stats (both need fenwick/high_danger from pass 3)
            .with_columns(
                *hd_exprs,
                (pl.col("goal") * pl.col("goal_w").fill_null(0.0)).alias("goal_adj"),
                (pl.col("pred_goal") * pl.col("xg_w").fill_null(0.0)).alias("pred_goal_adj"),
                (pl.col("shot") * pl.col("shot_w").fill_null(0.0)).alias("shot_adj"),
                (pl.col("fenwick") * pl.col("fenwick_w").fill_null(0.0)).alias("fenwick_adj"),
                (pl.col("corsi") * pl.col("corsi_w").fill_null(0.0)).alias("corsi_adj"),
            )
            .drop(["score_bucket", "goal_w", "xg_w", "shot_w", "fenwick_w", "corsi_w"])
            .collect()
        ),
    )


def add_positions(
    pbp: pl.DataFrame | pl.LazyFrame, rosters: pl.DataFrame | pl.LazyFrame
) -> pl.DataFrame | pl.LazyFrame:
    """Adds position data to the play-by-play data from evolving-hockey.com."""
    # Capture the columns before we go Lazy, and initialize the Lazy API
    is_lazy = isinstance(pbp, pl.LazyFrame)
    lf: pl.LazyFrame = pbp.lazy()
    rosters_lf: pl.LazyFrame = rosters.lazy()

    # Pre-select roster subsets to keep the joins lightweight
    rosters_player = rosters_lf.select(["game_id", "player", "eh_id", "position"])
    rosters_team_num = rosters_lf.select(["game_id", "team_jersey", "player", "eh_id", "position"])

    player_cols = [col for col in pbp.columns if ("event_player" in col or "on_" in col) and ("s_on" not in col)]

    # Standard Player Joins
    for col in player_cols:
        lf = (
            lf.join(rosters_player, left_on=["game_id", col], right_on=["game_id", "eh_id"], how="left", coalesce=False)
            .rename({"eh_id": f"{col}_eh_id", "position": f"{col}_pos"})
            .drop(["game_id_right", "player"], strict=False)
        )

    # The "Explode and Rebuild" Line Change Logic
    for target_col in ["players_on", "players_off"]:
        # Create a temporary row index so we can stitch the exploded data back together
        lf = lf.with_row_index("row_id")

        # Split the comma-separated strings into lists, then explode them into rows
        exploded = (
            lf.select(["row_id", "game_id", target_col])
            .with_columns(pl.col(target_col).str.split(", ").alias("team_jersey"))
            .explode("team_jersey")
            .filter(pl.col("team_jersey") != "")
        )

        # Execute one single join for all line changes, instead of looping through columns
        joined = exploded.join(rosters_team_num, on=["game_id", "team_jersey"], how="left")

        # Group back by the row index, collecting the results into comma-separated strings
        rebuilt = joined.group_by("row_id", maintain_order=True).agg(
            pl.col("player").drop_nulls().alias(f"{target_col}_new"),
            pl.col("eh_id").drop_nulls().alias(f"{target_col}_eh_id"),
            pl.col("position").drop_nulls().alias(f"{target_col}_pos"),
        )

        # Merge the rebuilt strings back to the main DataFrame and clean up
        lf = (
            lf.join(rebuilt, on="row_id", how="left")
            .drop(["row_id", target_col])
            .rename({f"{target_col}_new": target_col})
            .with_columns(
                pl.col(target_col).list.join(", "),
                pl.col(f"{target_col}_eh_id").list.join(", "),
                pl.col(f"{target_col}_pos").list.join(", "),
            )
        )

    # Position Aggregations
    player_groups = ["event", "opp"]
    player_types = {"f": ["L", "C", "R"], "d": ["D"], "g": ["G"]}

    lf = lf.with_row_index("__pid")

    for player_group in player_groups:
        slot_dfs = [
            lf.select(
                "__pid",
                pl.col(f"{player_group}_on_{i}").alias("name"),
                pl.col(f"{player_group}_on_{i}_pos").alias("pos"),
                pl.col(f"{player_group}_on_{i}_eh_id").alias("id"),
            )
            for i in range(1, 8)
        ]
        stacked = pl.concat(slot_dfs)

        agg_exprs = []
        for pos_group, positions in player_types.items():
            pos_filter = pl.col("pos").is_in(positions)
            agg_exprs += [
                pl.col("name").filter(pos_filter).sort().str.join(", ").alias(f"{player_group}_on_{pos_group}"),
                pl.col("id").filter(pos_filter).sort().str.join(", ").alias(f"{player_group}_on_{pos_group}_eh_id"),
            ]

        aggregated = stacked.filter(pl.col("name").is_not_null()).group_by("__pid").agg(*agg_exprs)

        lf = lf.join(aggregated, on="__pid", how="left")

    lf = lf.drop("__pid")

    # Execute the query graph and return
    return cast(pl.DataFrame, lf.collect()) if not is_lazy else lf


def prep_pbp(
    pbp: pl.DataFrame | list[pl.DataFrame],
    shifts: pl.DataFrame | list[pl.DataFrame],
    columns: Literal["light", "full", "all"] = "full",
    disable_progress_bar: bool = False,
) -> pl.DataFrame:
    """Prepares a play-by-play dataframe using EvolvingHockey data, adding stats and position info.

    Accepts any narwhals-compatible DataFrame (Polars, pandas, etc.) for both ``pbp`` and ``shifts``.
    Internally converts to Polars, processes, and returns a ``pl.DataFrame``.

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

    Returns:
        pl.DataFrame with processed play-by-play data.

    Examples:
        >>> import polars as pl
        >>> from chickenstats.evolving_hockey.pbp import prep_pbp
        >>> pbp = prep_pbp(pl.read_csv("raw_pbp.csv"), pl.read_csv("raw_shifts.csv"))
    """
    if not isinstance(pbp, list):
        pbp = [pbp]
    if not isinstance(shifts, list):
        shifts = [shifts]

    if len(pbp) != len(shifts):
        raise DataMismatchError("Number of play-by-play and shift CSV files does not match")

    def _to_polars(frame) -> pl.DataFrame:
        """Convert any narwhals-compatible frame to a Polars DataFrame."""
        if isinstance(frame, pl.DataFrame):
            return frame
        return cast(pl.DataFrame, pl.from_arrow(nw.from_native(frame, eager_only=True).to_arrow()))

    # Base column list ("light" mode)
    base_cols = [
        "id",
        "season",
        "session",
        "game_id",
        "game_date",
        "event_index",
        "game_period",
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
        "event_on_f",
        "event_on_f_eh_id",
        "event_on_d",
        "event_on_d_eh_id",
        "event_on_g",
        "event_on_g_eh_id",
        "opp_on_f",
        "opp_on_f_eh_id",
        "opp_on_d",
        "opp_on_d_eh_id",
        "opp_on_g",
        "opp_on_g_eh_id",
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
        "block",
        "corsi",
        "corsi_adj",
        "fenwick",
        "fenwick_adj",
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
            rosters = munge_rosters(_to_polars(shifts_raw))
            pbp_clean = munge_pbp(_to_polars(pbp_raw))
            pbp_clean = add_positions(pbp_clean, rosters)

            cols = list(base_cols)

            if columns in ["full", "all"]:
                # Insert individual on-ice player slots after the position-group summary columns
                event_on_cols = [
                    x for i in range(1, 8) for x in (f"event_on_{i}", f"event_on_{i}_eh_id", f"event_on_{i}_pos")
                ]
                opp_on_cols = [x for i in range(1, 8) for x in (f"opp_on_{i}", f"opp_on_{i}_eh_id", f"opp_on_{i}_pos")]

                event_pos = cols.index("event_on_g_eh_id") + 1
                cols[event_pos:event_pos] = event_on_cols

                opp_pos = cols.index("opp_on_g_eh_id") + 1
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

    return pl.concat(results, how="diagonal_relaxed")
