import pytest

from chickenstats.chicken_nhl._fixes import (
    api_events_fixes,
    api_rosters_fixes,
    html_events_fixes,
    html_rosters_fixes,
    individual_shifts_fixes,
    rosters_fixes,
)


# ---------------------------------------------------------------------------
# html_rosters_fixes
# ---------------------------------------------------------------------------


class TestHtmlRostersFixes:
    @pytest.mark.parametrize(
        "player_name", ["ROSS JOHNSTON", "SEBASTIAN AHO", "CONNOR CARRICK", "JESPER BRATT", "JACK HUGHES"]
    )
    def test_scratches_get_scratch_status(self, player_name):
        player = {"player_name": player_name, "status": "ACTIVE"}
        result = html_rosters_fixes(game_id=2019020665, player=player)
        assert result["status"] == "SCRATCH"

    def test_non_scratch_player_unchanged(self):
        player = {"player_name": "TAYLOR HALL", "status": "ACTIVE"}
        result = html_rosters_fixes(game_id=2019020665, player=player)
        assert result["status"] == "ACTIVE"

    def test_different_game_id_not_affected(self):
        player = {"player_name": "ROSS JOHNSTON", "status": "ACTIVE"}
        result = html_rosters_fixes(game_id=2023020001, player=player)
        assert result["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# api_rosters_fixes
# ---------------------------------------------------------------------------


class TestApiRostersFixes:
    def test_game_2013020971_returns_horton(self):
        result = api_rosters_fixes(season=20132014, session="R", game_id=2013020971)
        assert result["player_name"] == "NATHAN HORTON"
        assert result["api_id"] == 8470596
        assert result["team"] == "CBJ"

    def test_game_2013020971_all_required_fields(self):
        result = api_rosters_fixes(season=20132014, session="R", game_id=2013020971)
        required_fields = [
            "season",
            "session",
            "game_id",
            "team",
            "team_venue",
            "player_name",
            "first_name",
            "last_name",
            "api_id",
            "eh_id",
            "team_jersey",
            "jersey",
            "position",
            "headshot_url",
        ]
        for field in required_fields:
            assert field in result

    def test_game_2013020971_passes_season_and_session(self):
        result = api_rosters_fixes(season=20132014, session="R", game_id=2013020971)
        assert result["season"] == 20132014
        assert result["session"] == "R"
        assert result["game_id"] == 2013020971

    def test_other_game_returns_empty_dict(self):
        result = api_rosters_fixes(season=20232024, session="R", game_id=2023020001)
        assert result == {}


# ---------------------------------------------------------------------------
# rosters_fixes
# ---------------------------------------------------------------------------


class TestRostersFixes:
    def test_game_2015020508_ana5_updates_api_id(self):
        player_info = {"team_jersey": "ANA5", "api_id": None, "headshot_url": ""}
        result = rosters_fixes(game_id=2015020508, player_info=player_info)
        assert result["api_id"] == 8473560

    def test_game_2015020508_ana5_updates_headshot(self):
        player_info = {"team_jersey": "ANA5", "api_id": None, "headshot_url": ""}
        result = rosters_fixes(game_id=2015020508, player_info=player_info)
        assert "8473560" in result["headshot_url"]

    def test_game_2015020508_other_jersey_unchanged(self):
        player_info = {"team_jersey": "ANA10", "api_id": 9999999, "headshot_url": ""}
        result = rosters_fixes(game_id=2015020508, player_info=player_info)
        assert result["api_id"] == 9999999

    def test_game_2015021197_lak13_updates_api_id(self):
        player_info = {"team_jersey": "LAK13", "api_id": None, "headshot_url": ""}
        result = rosters_fixes(game_id=2015021197, player_info=player_info)
        assert result["api_id"] == 8475160

    def test_game_2015021197_lak13_updates_headshot(self):
        player_info = {"team_jersey": "LAK13", "api_id": None, "headshot_url": ""}
        result = rosters_fixes(game_id=2015021197, player_info=player_info)
        assert "8475160" in result["headshot_url"]

    def test_game_2015021197_other_jersey_unchanged(self):
        player_info = {"team_jersey": "LAK10", "api_id": 9999999, "headshot_url": ""}
        result = rosters_fixes(game_id=2015021197, player_info=player_info)
        assert result["api_id"] == 9999999

    def test_other_game_id_unchanged(self):
        player_info = {"team_jersey": "ANA5", "api_id": 9999999, "headshot_url": ""}
        result = rosters_fixes(game_id=2023020001, player_info=player_info)
        assert result["api_id"] == 9999999


# ---------------------------------------------------------------------------
# shifts_fixes
# ---------------------------------------------------------------------------


class TestShiftsFixes:
    def test_sam_lafferty_nbsp_period_gets_fixed(self):
        shift = {"period": "\xa0", "shift_count": "", "shift_start": "", "shift_end": ""}
        result = individual_shifts_fixes(game_id=2025020551, player_name="SAM LAFFERTY", shift_dict=shift)
        assert result["period"] == "1"
        assert result["shift_count"] == "8"
        assert result["shift_start"] == "16:46 / 3:16"
        assert result["shift_end"] == "17:45 / 2:15"

    def test_sam_lafferty_normal_period_unchanged(self):
        shift = {"period": "2", "shift_count": "5", "shift_start": "10:00 / 10:00", "shift_end": "11:00 / 9:00"}
        result = individual_shifts_fixes(game_id=2025020551, player_name="SAM LAFFERTY", shift_dict=shift)
        assert result["period"] == "2"

    def test_other_player_unchanged(self):
        shift = {"period": "\xa0", "shift_count": "", "shift_start": "", "shift_end": ""}
        result = individual_shifts_fixes(game_id=2025020551, player_name="TYLER MOTTE", shift_dict=shift)
        assert result["period"] == "\xa0"

    def test_other_game_id_unchanged(self):
        shift = {"period": "\xa0", "shift_count": "", "shift_start": "", "shift_end": ""}
        result = individual_shifts_fixes(game_id=2023020001, player_name="SAM LAFFERTY", shift_dict=shift)
        assert result["period"] == "\xa0"


# ---------------------------------------------------------------------------
# api_events_fixes — description correction patches
# ---------------------------------------------------------------------------


class TestHtmlEventsFixes:
    def test_game_2023020838_event_216_description_patched(self):
        event = {"event_idx": 216, "description": ""}
        result = html_events_fixes(game_id=2023020838, event=event)
        assert "RODRIGUES" in result["description"]
        assert "HIGH-STICKING" in result["description"]

    def test_game_2023020838_other_event_unchanged(self):
        event = {"event_idx": 100, "description": "original"}
        result = html_events_fixes(game_id=2023020838, event=event)
        assert result["description"] == "original"

    def test_game_2023021279_event_264_description_patched(self):
        event = {"event_idx": 264, "description": ""}
        result = html_events_fixes(game_id=2023021279, event=event)
        assert "O'CONNOR" in result["description"]
        assert "SLASHING" in result["description"]

    def test_game_2023021279_other_event_unchanged(self):
        event = {"event_idx": 100, "description": "original"}
        result = html_events_fixes(game_id=2023021279, event=event)
        assert result["description"] == "original"
