"""Rewrites chicken_nhl output in the shape of the Evolving-Hockey csv exports, for the evolving_hockey tests.

The exports are for subscribers and cannot ship with the tests, so the fixtures are built here from the games saved
for the chicken_nhl tests. The columns, the dotted team codes and the order of the event players follow the exports.
The numbers come from chicken_nhl, so comparing the two modules checks the aggregation and not the data, and the
hand-built rows in ``test_edge_rows.py`` cover what this module cannot show on its own.

The GAR and xGAR frames hold the real roster of each game. Their rating columns are placeholders worked out from ice
time, and pred_goal is worked out from distance; neither is a rating or a model. Shootout rows have no export to copy, so they carry what chicken_nhl gives them.
"""

import polars as pl

DOTTED_TEAMS = {"SJS": "S.J", "NJD": "N.J", "TBL": "T.B", "LAK": "L.A"}

# The exports shorten these first names, where chicken_nhl keeps the name from the NHL API
SHORTENED_NAMES = {"ALEXANDRE": "ALEX", "ALEXANDER": "ALEX", "CHRISTOPHER": "CHRIS"}

# Events with no team in the exports
NO_TEAM_EVENTS = ["STOP", "ANTHEM", "PGSTR", "PGEND", "PSTR", "PEND", "EISTR", "EIEND", "GEND", "SOC", "PBOX"]

ON_ICE_SLOTS = range(1, 8)

PBP_COLUMNS = [
    "season",
    "game_id",
    "game_date",
    "session",
    "event_index",
    "game_period",
    "game_seconds",
    "clock_time",
    "event_type",
    "event_description",
    "event_detail",
    "event_zone",
    "event_team",
    "event_player_1",
    "event_player_2",
    "event_player_3",
    "event_length",
    "coords_x",
    "coords_y",
    "num_on",
    "num_off",
    "players_on",
    "players_off",
    *[f"home_on_{slot}" for slot in ON_ICE_SLOTS],
    *[f"away_on_{slot}" for slot in ON_ICE_SLOTS],
    "home_goalie",
    "away_goalie",
    "home_team",
    "away_team",
    "home_skaters",
    "away_skaters",
    "home_score",
    "away_score",
    "game_score_state",
    "game_strength_state",
    "home_zone",
    "pbp_distance",
    "event_distance",
    "event_angle",
    "home_zonestart",
    "face_index",
    "pen_index",
    "shift_index",
    "pred_goal",
]


def dotted_team(column: str) -> pl.Expr:
    """A team code as the exports write it."""
    return pl.col(column).replace(DOTTED_TEAMS)


def export_id(expr: pl.Expr) -> pl.Expr:
    """An eh_id as the exports write it: shortened first names, and two dots after a first name that ends in one."""
    shortened = expr.str.replace_many(list(SHORTENED_NAMES), list(SHORTENED_NAMES.values()))
    return shortened.str.replace(r"^([A-Z]\.[A-Z])\.", "$1..")


def _flipped(state: pl.Expr) -> pl.Expr:
    """A strength or score state from the other team's side."""
    split = state.str.split("v")
    return split.list.get(1) + "v" + split.list.get(0)


def _jerseys_of(pbp: pl.DataFrame, column: str, rosters: pl.DataFrame) -> pl.Series:
    """Rewrite a comma-separated list of eh_ids as the comma-separated jersey codes the exports hold."""
    dotted_jersey = pl.col("team_jersey").str.replace_many(list(DOTTED_TEAMS), list(DOTTED_TEAMS.values()))
    jerseys = {
        (game, eh_id): jersey for game, eh_id, jersey in rosters.select("game_id", "eh_id", dotted_jersey).rows()
    }

    return pl.Series(
        [
            None if players is None else ", ".join(jerseys[(game_id, player)] for player in players.split(", "))
            for game_id, players in pbp.select("game_id", column).rows()
        ],
        dtype=pl.String,
    )


def _on_ice_slots(side: str) -> list[pl.Expr]:
    """Spread one team's on-ice list over the numbered columns, keeping the goalie as the exports do."""
    players = pl.col(f"{side}_on_eh_id").str.split(", ")
    return [export_id(players.list.get(slot - 1, null_on_oob=True)).alias(f"{side}_on_{slot}") for slot in ON_ICE_SLOTS]


def _penalty_shot_goalie_on_ice(pbp: pl.DataFrame) -> pl.DataFrame:
    """Put the shooting team's goalie back on the ice for a penalty shot, as the exports leave him."""
    for side in ("home", "away"):
        goalie = pl.col(f"{side}_goalie_eh_id").fill_null(strategy="forward").over("game_id")
        is_shooter = pl.col("is_penalty_shot") & (pl.col("event_team") == pl.col(f"{side}_team"))
        on_ice = pl.when(is_shooter).then(pl.col(f"{side}_on_eh_id") + ", " + goalie).otherwise(f"{side}_on_eh_id")
        pbp = pbp.with_columns(
            on_ice.alias(f"{side}_on_eh_id"),
            pl.when(is_shooter).then(goalie).otherwise(f"{side}_goalie_eh_id").alias(f"{side}_goalie_eh_id"),
        )

    return pbp


def _period_length(session: pl.Expr, period: pl.Expr) -> pl.Expr:
    """The seconds in a period: regular-season overtime is five minutes, and a shootout has no clock."""
    is_regular_season = session == "R"
    return (
        pl.when(is_regular_season & (period == 5))
        .then(0)
        .when(is_regular_season & (period == 4))
        .then(300)
        .otherwise(1200)
    )


def to_eh_pbp(pbp: pl.DataFrame, rosters: pl.DataFrame) -> pl.DataFrame:
    """Rewrite a chicken_nhl play-by-play as an Evolving-Hockey play-by-play export.

    Parameters:
        pbp: ``Scraper.play_by_play``.
        rosters: ``Scraper.rosters``.
    """
    is_block = pl.col("event") == "BLOCK"
    is_teammate_block = pl.col("teammate_block") == 1
    is_opponent_block = is_block & ~is_teammate_block
    is_faceoff = pl.col("event") == "FAC"
    home_won = pl.col("event_team") == pl.col("home_team")

    # chicken_nhl writes the blocker first and gives the block to his team, where the exports start from the shooter
    shooting_team = pl.when(is_opponent_block).then("opp_team").otherwise("event_team")

    # A faceoff is written away player first, whoever won it
    player_1 = (
        pl.when(is_block)
        .then("player_2_eh_id")
        .when(is_faceoff & home_won)
        .then("player_2_eh_id")
        .otherwise("player_1_eh_id")
    )
    player_2 = (
        pl.when(is_teammate_block)
        .then(None)
        .when(is_opponent_block)
        .then("player_1_eh_id")
        .when(is_faceoff & home_won)
        .then("player_1_eh_id")
        .otherwise("player_2_eh_id")
    )

    event_is_home = pl.col("event_team") == pl.col("home_team")
    home_strength = pl.when(event_is_home).then("strength_state").otherwise(_flipped(pl.col("strength_state")))

    zone = pl.col("zone").replace({"OFF": "Off", "DEF": "Def", "NEU": "Neu"})
    home_zone = pl.when(event_is_home).then(zone).otherwise(zone.replace({"Off": "Def", "Def": "Off"}))

    is_change = pl.col("event") == "CHANGE"
    is_shot = pl.col("event").is_in(["GOAL", "SHOT", "MISS", "BLOCK"])
    is_penalty = pl.col("event") == "PENL"

    event_detail = (
        pl.when(is_shot)
        .then(pl.col("shot_type").str.to_titlecase())
        .when(is_penalty)
        .then(pl.col("penalty_length").cast(pl.String) + "min")
    )

    is_shootout = (pl.col("session") == "R") & (pl.col("period") == 5)
    is_penalty_shot = (pl.col("strength_state") == "1v0") & ~is_shootout

    seconds_left = _period_length(pl.col("session"), pl.col("period")) - pl.col("period_seconds")
    clock_time = (seconds_left // 60).cast(pl.String) + ":" + (seconds_left % 60).cast(pl.String).str.zfill(2)

    # The offline games have no expected goals, so this stands in for them and is not a model
    is_unblocked = pl.col("event").is_in(["GOAL", "SHOT", "MISS"])
    pred_goal = pl.when(is_unblocked).then((1 / (1 + pl.col("event_distance").fill_null(50.0))).round(6))

    converted = pbp.with_columns(is_penalty_shot.alias("is_penalty_shot"), pred_goal.alias("pred_goal"))
    converted = _penalty_shot_goalie_on_ice(converted)

    return converted.with_columns(
        pl.col("event_idx").alias("event_index"),
        pl.col("period").alias("game_period"),
        clock_time.alias("clock_time"),
        pl.col("event").alias("event_type"),
        pl.col("description")
        .str.replace_many(list(DOTTED_TEAMS), list(DOTTED_TEAMS.values()))
        .alias("event_description"),
        event_detail.alias("event_detail"),
        pl.when(~is_change).then(zone).alias("event_zone"),
        pl.when(pl.col("event").is_in(NO_TEAM_EVENTS))
        .then(None)
        .otherwise(shooting_team)
        .replace(DOTTED_TEAMS)
        .alias("event_team"),
        export_id(player_1).alias("event_player_1"),
        export_id(player_2).alias("event_player_2"),
        export_id(pl.col("player_3_eh_id")).alias("event_player_3"),
        pl.col("change_on_count").cast(pl.Float64).alias("num_on"),
        pl.col("change_off_count").cast(pl.Float64).alias("num_off"),
        _jerseys_of(pbp, "change_on_eh_id", rosters).alias("players_on"),
        _jerseys_of(pbp, "change_off_eh_id", rosters).alias("players_off"),
        *_on_ice_slots("home"),
        *_on_ice_slots("away"),
        export_id(pl.col("home_goalie_eh_id")).alias("home_goalie"),
        export_id(pl.col("away_goalie_eh_id")).alias("away_goalie"),
        dotted_team("home_team").alias("home_team"),
        dotted_team("away_team").alias("away_team"),
        (pl.col("home_score").cast(pl.String) + "v" + pl.col("away_score").cast(pl.String)).alias("game_score_state"),
        home_strength.alias("game_strength_state"),
        pl.when(~is_change).then(home_zone).alias("home_zone"),
        pl.lit(None, dtype=pl.Float64).alias("home_zonestart"),
        is_faceoff.cast(pl.Int64).cum_sum().over("game_id").alias("face_index"),
        is_penalty.cast(pl.Int64).cum_sum().over("game_id").alias("pen_index"),
        is_change.cast(pl.Int64).cum_sum().over("game_id").alias("shift_index"),
    ).select(PBP_COLUMNS)


def to_eh_shifts(shifts: pl.DataFrame, pbp: pl.DataFrame) -> pl.DataFrame:
    """Rewrite chicken_nhl shifts as an Evolving-Hockey shifts export.

    Parameters:
        shifts: ``Scraper.shifts``.
        pbp: ``Scraper.play_by_play``, for the date of each game.
    """
    games = pbp.select("game_id", "game_date").unique()
    teams = pbp.select("game_id", "home_team", "away_team").unique()

    period_start = (pl.col("period") - 1) * 1200

    return (
        shifts.join(games, on="game_id")
        .join(teams, on="game_id")
        .select(
            export_id(pl.col("eh_id")).alias("player"),
            pl.col("team_jersey").str.replace_many(list(DOTTED_TEAMS), list(DOTTED_TEAMS.values())).alias("team_num"),
            "position",
            "game_id",
            "game_date",
            "season",
            "session",
            dotted_team("team").alias("team"),
            pl.when(pl.col("team") == pl.col("home_team"))
            .then("away_team")
            .otherwise("home_team")
            .replace(DOTTED_TEAMS)
            .alias("opponent"),
            "is_home",
            pl.col("period").alias("game_period"),
            pl.col("shift_count").alias("shift_num"),
            (period_start + pl.col("start_time_seconds")).alias("seconds_start"),
            (period_start + pl.col("end_time_seconds")).alias("seconds_end"),
            pl.col("duration_seconds").alias("seconds_duration"),
            pl.col("start_time").alias("shift_start"),
            pl.col("end_time").alias("shift_end"),
            "duration",
            pl.lit(0).alias("shift_mod"),
        )
    )


def _rating_frame(shifts: pl.DataFrame, goalies: bool) -> pl.DataFrame:
    """One row per player, season and team, with the identity columns of the GAR and xGAR exports."""
    two_digit_years = pl.col("season").cast(pl.String)
    positions = pl.col("position") == "G" if goalies else pl.col("position") != "G"

    return (
        shifts.filter(positions)
        .group_by("eh_id", "api_id", "player_name", "season", "team", "position")
        .agg(pl.col("game_id").n_unique().alias("GP"), (pl.col("duration_seconds").sum() / 60).round(1).alias("TOI"))
        .sort("season", "team", "eh_id")
        .select(
            pl.col("player_name").str.to_titlecase().alias("Player"),
            export_id(pl.col("eh_id")).alias("EH_ID"),
            pl.col("api_id").alias("API ID"),
            (two_digit_years.str.slice(2, 2) + "-" + two_digit_years.str.slice(6, 2)).alias("Season"),
            dotted_team("team").alias("Team"),
            pl.col("position").alias("Position"),
            pl.lit("L").alias("Catches" if goalies else "Shoots"),
            pl.lit("2000-01-01").alias("Birthday"),
            pl.lit(25).alias("Age"),
            pl.lit(None, dtype=pl.Int64).alias("Draft Yr"),
            pl.lit(None, dtype=pl.String).alias("Draft Rd"),
            pl.lit(None, dtype=pl.String).alias("Draft Ov"),
            "GP",
            "TOI",
        )
    )


def _placeholder(columns: list[str]) -> list[pl.Expr]:
    """Fill rating columns with a number worked out from ice time, which is not a rating."""
    return [(pl.col("TOI") / 100).round(1).alias(column) for column in columns]


def to_eh_gar_skaters(shifts: pl.DataFrame) -> pl.DataFrame:
    """Build a frame with the columns of the Evolving-Hockey skater GAR export, from ``Scraper.shifts``."""
    ratings = ["EVO_GAR", "EVD_GAR", "PPO_GAR", "SHD_GAR", "Take_GAR", "Draw_GAR", "Off_GAR", "Def_GAR", "Pens_GAR"]

    return (
        _rating_frame(shifts, goalies=False)
        .rename({"TOI": "TOI_All"})
        .with_columns(pl.col("TOI_All").alias("TOI"))
        .with_columns(
            pl.col("TOI_All").alias("TOI_EV"),
            pl.lit(0.0).alias("TOI_PP"),
            pl.lit(0.0).alias("TOI_SH"),
            *_placeholder([*ratings, "GAR", "WAR", "SPAR"]),
        )
        .drop("TOI")
    )


def to_eh_gar_goalies(shifts: pl.DataFrame) -> pl.DataFrame:
    """Build a frame with the columns of the Evolving-Hockey goalie GAR export, from ``Scraper.shifts``."""
    ratings = ["EVD_GAR", "SHD_GAR", "Take_GAR", "Draw_GAR", "GAR", "WAR", "SPAR"]

    return (
        _rating_frame(shifts, goalies=True)
        .with_columns(
            pl.col("TOI").alias("TOI_EV"),
            pl.lit(0.0).alias("TOI_SH"),
            pl.lit(0).alias("FA_EV"),
            pl.lit(0).alias("FA_SH"),
            *_placeholder(ratings),
        )
        .drop("TOI")
    )


def to_eh_xgar_skaters(shifts: pl.DataFrame) -> pl.DataFrame:
    """Build a frame with the columns of the Evolving-Hockey skater xGAR export, from ``Scraper.shifts``."""
    ratings = ["xEVO_GAR", "xEVD_GAR", "xPPO_GAR", "xSHD_GAR", "Take_GAR", "Draw_GAR", "xOff_GAR", "xDef_GAR"]

    return (
        _rating_frame(shifts, goalies=False)
        .rename({"TOI": "TOI_All"})
        .with_columns(pl.col("TOI_All").alias("TOI"))
        .with_columns(*_placeholder([*ratings, "Pens_GAR", "xGAR", "xWAR", "xSPAR"]))
        .drop("TOI")
    )


def csv_round_trip(frame: pl.DataFrame) -> pl.DataFrame:
    """Write a frame to csv and read it back, so it reaches ``prep_pbp`` the way a downloaded export does."""
    return pl.read_csv(frame.write_csv().encode(), infer_schema_length=None)
