"""Hand-built rows in the shape of the Evolving-Hockey exports, for what the converted games cannot show.

Each game here has two players and a goalie a side. The rows use the order and the codes of the exports: a faceoff
names the away player first whoever won it, a blocked shot starts from the shooter, and four teams have dotted codes.
"""

import polars as pl
import pytest

from chickenstats.evolving_hockey import prep_gar, prep_lines, prep_pbp, prep_stats, prep_team_stats
from chickenstats.exceptions import InvalidInputError

from .eh_converter import PBP_COLUMNS

GAME_ID = 2023029001
STRING_COLUMNS = [
    "game_date",
    "session",
    "clock_time",
    "event_type",
    "event_description",
    "event_detail",
    "event_zone",
    "event_team",
    "event_player_1",
    "event_player_2",
    "event_player_3",
    "players_on",
    "players_off",
    *[f"{side}_on_{slot}" for side in ("home", "away") for slot in range(1, 8)],
    "home_goalie",
    "away_goalie",
    "home_team",
    "away_team",
    "game_score_state",
    "game_strength_state",
    "home_zone",
]
SKATERS = {"N.J": ["JACK.HUGHES", "DOUGIE.HAMILTON"], "S.J": ["TOMAS.HERTL", "MARIO.FERRARO"]}
GOALIES = {"N.J": "AKIRA.SCHMID", "S.J": "KAAPO.KAHKONEN"}
POSITIONS = {"JACK.HUGHES": "C", "DOUGIE.HAMILTON": "D", "TOMAS.HERTL": "C", "MARIO.FERRARO": "D"}


def event(event_type: str, seconds: int = 10, game_id: int = GAME_ID, **columns) -> dict:
    """One export row of a 2v2 game, with both goalies on the ice unless the row says otherwise."""
    return {
        **dict.fromkeys(PBP_COLUMNS),
        "season": 20232024,
        "game_id": game_id,
        "game_date": "2023-10-10",
        "session": "R",
        "game_period": 1,
        "game_seconds": seconds,
        "clock_time": "19:50",
        "event_type": event_type,
        "event_length": 1,
        "home_team": "N.J",
        "away_team": "S.J",
        "home_skaters": 2,
        "away_skaters": 2,
        "home_score": 0,
        "away_score": 0,
        "game_score_state": "0v0",
        "game_strength_state": "5v5",
        "home_goalie": GOALIES["N.J"],
        "away_goalie": GOALIES["S.J"],
        "home_on_1": "JACK.HUGHES",
        "home_on_2": "DOUGIE.HAMILTON",
        "home_on_3": GOALIES["N.J"],
        "away_on_1": "TOMAS.HERTL",
        "away_on_2": "MARIO.FERRARO",
        "away_on_3": GOALIES["S.J"],
        **columns,
    }


def export(rows: list[dict]) -> pl.DataFrame:
    """Number the rows of each game and build a play-by-play export."""
    for index, row in enumerate(rows, start=1):
        row["event_index"] = index

    integers = ("season", "game_id", "event_index", "game_period", "game_seconds")
    schema = {c: pl.String if c in STRING_COLUMNS else pl.Int64 if c in integers else pl.Float64 for c in PBP_COLUMNS}
    return pl.DataFrame(rows, schema=schema, strict=False)


def shifts(game_ids: tuple[int, ...] = (GAME_ID,), extra: tuple[tuple[str, str, str], ...] = ()) -> pl.DataFrame:
    """A shifts export with one shift for each player: (player, jersey code, position) rows on top of the 2v2 game."""
    players = [
        (name, f"{team}{jersey}", POSITIONS[name]) for team in SKATERS for jersey, name in enumerate(SKATERS[team], 1)
    ]
    players += [(GOALIES[team], f"{team}30", "G") for team in GOALIES]
    players += list(extra)

    return pl.DataFrame(
        [
            {
                "player": player,
                "team_num": team_num,
                "position": position,
                "game_id": game_id,
                "season": 20232024,
                "session": "R",
                "team": team_num.rstrip("0123456789"),
            }
            for game_id in game_ids
            for player, team_num, position in players
        ]
    )


def prepped(rows: list[dict], **shift_options) -> pl.DataFrame:
    return prep_pbp(export(rows), shifts(**shift_options), disable_progress_bar=True)


def test_dotted_team_codes_are_normalized_on_both_sides():
    """A game between two dotted teams has one code for each team, as the event team and as the opposing team."""
    pbp = prepped([event("HIT", event_team="N.J", event_player_1="JACK.HUGHES", event_player_2="TOMAS.HERTL")])

    assert pbp.row(0, named=True)["event_team"] == "NJD"
    assert pbp.row(0, named=True)["opp_team"] == "SJS"


def test_team_stats_of_a_dotted_game_have_one_row_a_team():
    pbp = prepped(
        [
            event("SHOT", event_team="N.J", event_player_1="JACK.HUGHES", event_zone="Off", pred_goal=0.1),
            event("SHOT", 20, event_team="S.J", event_player_1="TOMAS.HERTL", event_zone="Off", pred_goal=0.1),
        ]
    )

    team_stats = prep_team_stats(pbp, strengths=False, disable_progress_bar=True)

    assert sorted(team_stats["team"]) == ["NJD", "SJS"]
    assert team_stats["sf"].to_list() == [1, 1]
    assert team_stats["sa"].to_list() == [1, 1]


def test_a_faceoff_names_the_winner_first_whichever_team_won():
    """The export writes the away player first, so only a home win changes the order."""
    pbp = prepped(
        [
            event("FAC", 10, event_team="N.J", event_player_1="TOMAS.HERTL", event_player_2="JACK.HUGHES"),
            event("FAC", 20, event_team="S.J", event_player_1="TOMAS.HERTL", event_player_2="JACK.HUGHES"),
        ]
    )

    assert pbp["event_player_1_eh_id"].to_list() == ["JACK.HUGHES", "TOMAS.HERTL"]
    assert pbp["event_player_2_eh_id"].to_list() == ["TOMAS.HERTL", "JACK.HUGHES"]


def test_a_blocked_shot_keeps_the_shooter_first():
    pbp = prepped([event("BLOCK", event_team="S.J", event_player_1="MARIO.FERRARO", event_player_2="JACK.HUGHES")])

    assert pbp["event_player_1_eh_id"].to_list() == ["MARIO.FERRARO"]
    assert pbp["event_player_2_eh_id"].to_list() == ["JACK.HUGHES"]


def test_a_dotted_team_keeps_its_line_changes():
    """A jersey code from a dotted team finds its player, so the change list and its zone starts are not lost."""
    pbp = prepped(
        [
            event("CHANGE", event_team="N.J", players_on="N.J1, N.J2", players_off="N.J30", num_on=2, num_off=1),
            event("FAC", event_team="N.J", home_zone="Off", event_zone="Off", event_player_1="TOMAS.HERTL"),
        ]
    )

    assert pbp["players_on_eh_id"][0] == "JACK.HUGHES, DOUGIE.HAMILTON"
    assert pbp["players_off_eh_id"][0] == "AKIRA.SCHMID"
    assert pbp["ozs"][0] == 1


@pytest.mark.parametrize(
    ("team", "home_zone", "expected"),
    [("S.J", "Off", "DEF"), ("S.J", "Def", "OFF"), ("S.J", "Neu", "NEU"), ("N.J", "Off", "OFF"), ("N.J", "Def", "DEF")],
)
def test_a_zone_start_is_from_the_changing_team(team, home_zone, expected):
    """The zone of a faceoff is the home team's in the export, so it flips for the away team."""
    pbp = prepped([event("CHANGE", event_team=team), event("FAC", event_team="N.J", home_zone=home_zone)])

    assert pbp["zone_start"][0] == expected


def test_a_faceoff_in_another_game_at_the_same_second_is_not_borrowed():
    """A line change takes its zone from the next faceoff of its own game, when one file holds several games."""
    other_game = GAME_ID + 1
    rows = [
        event("CHANGE", event_team="N.J"),
        event("HIT", game_id=GAME_ID, event_team="N.J"),
        event("CHANGE", game_id=other_game, event_team="N.J", game_strength_state="5v4"),
        event("FAC", game_id=other_game, event_team="N.J", home_zone="Off", game_strength_state="4v5"),
    ]

    pbp = prepped(rows, game_ids=(GAME_ID, other_game))

    assert pbp.filter(pl.col("game_id") == GAME_ID, pl.col("event_type") == "CHANGE")["zone_start"].to_list() == ["OTF"]
    assert pbp.filter(pl.col("game_id") == GAME_ID, pl.col("event_type") == "CHANGE")["strength_state"].to_list() == [
        "5v5"
    ]


def test_an_illegal_strength_state_stays_illegal():
    """The export uses 'illegal' for a state the scraper could not work out, and the row is kept."""
    pbp = prepped([event("HIT", event_team="S.J", game_strength_state="illegal")])

    assert pbp["strength_state"].to_list() == ["illegal"]


def test_two_players_with_one_name_stay_apart():
    """A shared name in the export finds the player on the right team, and the second one has the suffix."""
    aho = "SEBASTIAN.AHO"
    extra = ((aho, "N.J20", "C"), (aho, "S.J25", "D"))
    pbp = prepped(
        [event("HIT", event_team="N.J", event_player_1=aho, event_player_2=aho, home_on_1=aho, away_on_1=aho)],
        extra=extra,
    )
    row = pbp.row(0, named=True)

    assert (row["event_player_1_eh_id"], row["event_player_1_pos"]) == ("SEBASTIAN.AHO", "C")
    assert (row["event_player_2_eh_id"], row["event_player_2_pos"]) == ("SEBASTIAN.AHO2", "D")
    assert row["event_player_1"] == row["event_player_2"] == "SEBASTIAN AHO"


def test_names_and_ids_follow_one_rule():
    """Accents, a shortened first name and a first name with dots read the same in shifts and play-by-play."""
    extra = (("TIM.STÜTZLE", "N.J18", "C"), ("J.T..MILLER", "N.J9", "C"), ("ALEXANDER.KERFOOT", "S.J15", "C"))
    pbp = prepped(
        [
            event(
                "GOAL",
                event_team="N.J",
                event_player_1="TIM.STUTZLE",
                event_player_2="J.T..MILLER",
                home_on_1="TIM.STUTZLE",
                home_on_2="J.T..MILLER",
                away_on_1="ALEX.KERFOOT",
            )
        ],
        extra=extra,
    )
    row = pbp.row(0, named=True)

    assert (row["event_player_1"], row["event_player_1_eh_id"]) == ("TIM STUTZLE", "TIM.STUTZLE")
    assert (row["event_player_2"], row["event_player_2_eh_id"]) == ("J.T. MILLER", "J.T.MILLER")
    assert (row["opp_on_1"], row["opp_on_1_eh_id"]) == ("ALEX KERFOOT", "ALEX.KERFOOT")


def test_gar_ids_follow_the_same_rule(raw_gar_skater_polars, raw_gar_goalie_polars):
    skaters = raw_gar_skater_polars.head(3).with_columns(
        pl.Series("EH_ID", ["A.J..GREER", "TIM.STÜTZLE", "SEBASTIAN.AHO2"]), pl.lit("23-24").alias("Season")
    )

    gar = prep_gar(skaters, raw_gar_goalie_polars.head(1))

    assert gar["eh_id"].to_list()[:3] == ["A.J.GREER", "TIM.STUTZLE", "SEBASTIAN.AHO2"]
    assert gar["player"].to_list()[:3] == ["A.J. GREER", "TIM STUTZLE", "SEBASTIAN AHO"]


def test_a_teammate_block_counts_as_a_blocked_attempt_with_no_blocker():
    pbp = prepped(
        [
            event(
                "BLOCK",
                event_team="N.J",
                event_player_1="JACK.HUGHES",
                event_description="N.J #86 HUGHES BLOCKED BY TEAMMATE, Wrist, Off. Zone",
            )
        ]
    )

    row = pbp.row(0, named=True)
    team_stats = prep_team_stats(pbp, strengths=False, disable_progress_bar=True)

    assert row["teammate_block"] == 1
    assert row["corsi"] == 1
    assert team_stats.filter(pl.col("team") == "NJD")["teammate_block"].to_list() == [1]
    assert team_stats.filter(pl.col("team") == "NJD")["bsf"].to_list() == [1]
    assert team_stats.filter(pl.col("team") == "SJS")["opp_teammate_block"].to_list() == [1]


def test_a_season_is_one_row_for_regular_season_and_playoffs():
    rows = [
        event("SHOT", event_team="N.J", event_player_1="JACK.HUGHES", event_zone="Off"),
        event("SHOT", game_id=GAME_ID + 1, session="P", event_team="N.J", event_player_1="JACK.HUGHES"),
    ]
    roster = pl.concat(
        [shifts(), shifts(game_ids=(GAME_ID + 1,)).with_columns(pl.lit("P").alias("session"))], how="vertical"
    )
    pbp = prep_pbp(export(rows), roster, disable_progress_bar=True)

    season = prep_stats(pbp, level="season", disable_progress_bar=True).filter(pl.col("eh_id") == "JACK.HUGHES")
    session = prep_stats(pbp, level="session", disable_progress_bar=True).filter(pl.col("eh_id") == "JACK.HUGHES")

    assert season["isf"].to_list() == [2]
    assert "session" not in season.columns
    assert sorted(session["isf"].to_list()) == [1, 1]


def test_an_unknown_columns_choice_raises():
    with pytest.raises(InvalidInputError, match="columns must be"):
        prep_pbp(export([event("HIT")]), shifts(), columns="medium", disable_progress_bar=True)  # ty: ignore[invalid-argument-type]


def test_an_unknown_position_raises():
    pbp = prepped([event("HIT", event_team="N.J", event_player_1="JACK.HUGHES", event_player_2="TOMAS.HERTL")])

    with pytest.raises(InvalidInputError, match="position must be"):
        prep_lines(pbp, position="g", disable_progress_bar=True)  # ty: ignore[invalid-argument-type]
