"""Hand-built rows in the shape of the Evolving-Hockey exports, for what the converted games cannot show.

Each game here has two players and a goalie a side. The rows use the order and the codes of the exports: a faceoff
names the away player first whoever won it, a blocked shot starts from the shooter, and four teams have dotted codes.
"""

import polars as pl
import pytest
from eh_converter import PBP_COLUMNS

from chickenstats.evolving_hockey import prep_pbp, prep_team_stats

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
AWAY_ZONE_FLIP = pytest.mark.xfail(strict=True, reason="the flip compares an upper-case zone with title-case names")
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


@pytest.mark.xfail(strict=True, reason="opp_team is built from the team codes before they are normalized")
def test_dotted_team_codes_are_normalized_on_both_sides():
    """A game between two dotted teams has one code for each team, as the event team and as the opposing team."""
    pbp = prepped([event("HIT", event_team="N.J", event_player_1="JACK.HUGHES", event_player_2="TOMAS.HERTL")])

    assert pbp.row(0, named=True)["event_team"] == "NJD"
    assert pbp.row(0, named=True)["opp_team"] == "SJS"


@pytest.mark.xfail(strict=True, reason="opp_team is built from the team codes before they are normalized")
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


@pytest.mark.xfail(strict=True, reason="the two event player columns are written to each other")
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


@pytest.mark.xfail(strict=True, reason="the two event player columns are written to each other")
def test_a_blocked_shot_keeps_the_shooter_first():
    pbp = prepped([event("BLOCK", event_team="S.J", event_player_1="MARIO.FERRARO", event_player_2="JACK.HUGHES")])

    assert pbp["event_player_1_eh_id"].to_list() == ["MARIO.FERRARO"]
    assert pbp["event_player_2_eh_id"].to_list() == ["JACK.HUGHES"]


@pytest.mark.xfail(strict=True, reason="the jersey codes in the roster keep their dots")
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
    [
        pytest.param("S.J", "Off", "DEF", marks=AWAY_ZONE_FLIP),
        pytest.param("S.J", "Def", "OFF", marks=AWAY_ZONE_FLIP),
        ("S.J", "Neu", "NEU"),
        ("N.J", "Off", "OFF"),
        ("N.J", "Def", "DEF"),
    ],
)
def test_a_zone_start_is_from_the_changing_team(team, home_zone, expected):
    """The zone of a faceoff is the home team's in the export, so it flips for the away team."""
    pbp = prepped([event("CHANGE", event_team=team), event("FAC", event_team="N.J", home_zone=home_zone)])

    assert pbp["zone_start"][0] == expected


@pytest.mark.xfail(strict=True, reason="the next faceoff is looked up across games")
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


@pytest.mark.xfail(strict=True, reason="an illegal strength state cannot be split in two")
def test_an_illegal_strength_state_stays_illegal():
    """The export uses 'illegal' for a state the scraper could not work out, and the row is kept."""
    pbp = prepped([event("HIT", event_team="S.J", game_strength_state="illegal")])

    assert pbp["strength_state"].to_list() == ["illegal"]
