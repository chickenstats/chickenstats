import polars as pl

from chickenstats.api._api_utils import (
    _line_stats_id,
    _player_stats_id,
    _prep_with_id,
    _sort_api_id_list,
    _team_stats_id,
    _to_int_list,
    _to_str_list,
)


class TestToIntList:
    def test_none(self):
        assert _to_int_list(None) is None

    def test_scalar(self):
        assert _to_int_list(42) == [42]

    def test_list(self):
        assert _to_int_list([1, "2", 3]) == [1, 2, 3]


class TestToStrList:
    def test_none(self):
        assert _to_str_list(None) is None

    def test_scalar(self):
        assert _to_str_list("20232024") == ["20232024"]

    def test_list(self):
        assert _to_str_list(["20222023", "20232024"]) == ["20222023", "20232024"]


class TestSortApiIdList:
    def test_sorted_numerically(self):
        df = pl.DataFrame({"ids": ["8474141, 8471675, 8478402"]})
        assert df.select(_sort_api_id_list("ids"))[0, 0] == "8471675_8474141_8478402"

    def test_single_id(self):
        df = pl.DataFrame({"ids": ["8471675"]})
        assert df.select(_sort_api_id_list("ids"))[0, 0] == "8471675"

    def test_null_is_empty_string(self):
        df = pl.DataFrame({"ids": [None]}, schema={"ids": pl.String})
        assert df.select(_sort_api_id_list("ids"))[0, 0] == ""


def _make_player_row() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": [2023020001],
            "period": [1],
            "score_state": ["0v0"],
            "strength_state": ["5v5"],
            "team": ["TOR"],
            "api_id": [8471675],
            "forwards_api_id": ["8474141, 8478402"],
            "defense_api_id": ["8480801, 8476981"],
            "own_goalie_api_id": [8476412],
            "opp_team": ["BOS"],
            "opp_forwards_api_id": ["8467400, 8470613"],
            "opp_defense_api_id": ["8470187, 8471676"],
            "opp_goalie_api_id": [8468001],
        }
    )


def _make_team_row() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": [2023020001],
            "period": [1],
            "score_state": ["0v0"],
            "strength_state": ["5v5"],
            "team": ["TOR"],
            "opp_team": ["BOS"],
        }
    )


class TestPlayerStatsId:
    def test_format(self):
        result = _make_player_row().select(_player_stats_id().alias("id"))[0, 0]
        assert len(result.split("-")) == 13
        assert result.startswith("2023020001-01-")
        assert "-5v5-TOR-" in result
        assert "8474141_8478402" in result  # forwards sorted numerically


class TestLineStatsId:
    def test_format(self):
        result = _make_player_row().select(_line_stats_id().alias("id"))[0, 0]
        assert len(result.split("-")) == 12  # one fewer than player: no individual api_id
        assert result.startswith("2023020001-01-")


class TestTeamStatsId:
    def test_format(self):
        result = _make_team_row().select(_team_stats_id().alias("id"))[0, 0]
        assert result == "2023020001-01-0v0-5v5-TOR-BOS"


class TestPrepWithId:
    def test_polars_output(self):
        result = _prep_with_id(_make_team_row(), _team_stats_id(), as_polars=True)
        assert isinstance(result, pl.DataFrame)
        assert result.columns[0] == "id"

    def test_dict_output(self):
        result = _prep_with_id(_make_team_row(), _team_stats_id())
        assert isinstance(result, list)
        assert "id" in result[0]
