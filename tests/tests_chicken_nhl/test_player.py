import pandas as pd
import polars as pl
import pytest

from chickenstats.chicken_nhl._player_names import correct_player_name
from chickenstats.chicken_nhl.player import Player


# ---------------------------------------------------------------------------
# correct_player_name — pure function, no network
# ---------------------------------------------------------------------------


class TestCorrectPlayerName:
    # ------------------------------------------------------------------
    # Name normalisation
    # ------------------------------------------------------------------

    def test_alexandre_replaced(self):
        name, _ = correct_player_name("ALEXANDRE CARRIER", season=20232024)
        assert name == "ALEX CARRIER"

    def test_alexander_replaced(self):
        name, _ = correct_player_name("ALEXANDER OVECHKIN", season=20232024)
        assert name == "ALEX OVECHKIN"

    def test_christopher_replaced(self):
        name, _ = correct_player_name("CHRISTOPHER TANEV", season=20232024)
        assert name == "CHRIS TANEV"

    def test_normal_name_unchanged(self):
        name, eh_id = correct_player_name("FILIP FORSBERG", season=20232024)
        assert name == "FILIP FORSBERG"
        assert eh_id == "FILIP.FORSBERG"

    def test_eh_id_dot_separated(self):
        _, eh_id = correct_player_name("RYAN NUGENT-HOPKINS", season=20232024)
        assert "." in eh_id

    # ------------------------------------------------------------------
    # correct_names_dict corrections
    # ------------------------------------------------------------------

    def test_misspelling_corrected_aj_greer(self):
        name, _ = correct_player_name("AJ GREER", season=20232024)
        assert name == "A.J. GREER"

    def test_misspelling_corrected_anthony_deangelo(self):
        name, _ = correct_player_name("ANTHONY DEANGELO", season=20232024)
        assert name == "TONY DEANGELO"

    def test_misspelling_corrected_cal_petersen(self):
        name, _ = correct_player_name("CAL PETERSEN", season=20232024)
        assert name == "CALVIN PETERSEN"

    # ------------------------------------------------------------------
    # Duplicate EH ID handling
    # ------------------------------------------------------------------

    def test_sebastian_aho_defender_gets_suffix(self):
        _, eh_id = correct_player_name("SEBASTIAN AHO", season=20232024, player_position="D")
        assert eh_id == "SEBASTIAN.AHO2"

    def test_sebastian_aho_forward_no_suffix(self):
        _, eh_id = correct_player_name("SEBASTIAN AHO", season=20232024, player_position="C")
        assert eh_id == "SEBASTIAN.AHO"

    def test_colin_white_recent_season_gets_suffix(self):
        _, eh_id = correct_player_name("COLIN WHITE", season=20162017)
        assert eh_id == "COLIN.WHITE2"

    def test_colin_white_old_season_no_suffix(self):
        _, eh_id = correct_player_name("COLIN WHITE", season=20152016)
        assert eh_id == "COLIN.WHITE"

    def test_elias_pettersson_van25_jersey_gets_suffix(self):
        _, eh_id = correct_player_name("ELIAS PETTERSSON", season=20232024, player_jersey="VAN25")
        assert eh_id == "ELIAS.PETTERSSON2"

    def test_elias_pettersson_jersey_25_gets_suffix(self):
        _, eh_id = correct_player_name("ELIAS PETTERSSON", season=20232024, player_jersey=25)
        assert eh_id == "ELIAS.PETTERSSON2"

    def test_elias_pettersson_defender_gets_suffix(self):
        _, eh_id = correct_player_name("ELIAS PETTERSSON", season=20232024, player_position="D")
        assert eh_id == "ELIAS.PETTERSSON2"

    def test_elias_pettersson_forward_no_suffix(self):
        _, eh_id = correct_player_name("ELIAS PETTERSSON", season=20232024, player_position="C")
        assert eh_id == "ELIAS.PETTERSSON"

    def test_erik_gustafsson_recent_season_gets_suffix(self):
        _, eh_id = correct_player_name("ERIK GUSTAFSSON", season=20152016)
        assert eh_id == "ERIK.GUSTAFSSON2"

    def test_erik_gustafsson_old_season_no_suffix(self):
        _, eh_id = correct_player_name("ERIK GUSTAFSSON", season=20142015)
        assert eh_id == "ERIK.GUSTAFSSON"

    def test_mikko_lehtonen_recent_season_gets_suffix(self):
        _, eh_id = correct_player_name("MIKKO LEHTONEN", season=20202021)
        assert eh_id == "MIKKO.LEHTONEN2"

    def test_nathan_smith_recent_season_gets_suffix(self):
        _, eh_id = correct_player_name("NATHAN SMITH", season=20212022)
        assert eh_id == "NATHAN.SMITH2"

    def test_daniil_tarasov_goalie_gets_suffix(self):
        _, eh_id = correct_player_name("DANIIL TARASOV", season=20232024, player_position="G")
        assert eh_id == "DANIIL.TARASOV2"

    def test_daniil_tarasov_non_goalie_no_suffix(self):
        _, eh_id = correct_player_name("DANIIL TARASOV", season=20232024, player_position="D")
        assert eh_id == "DANIIL.TARASOV"

    # ------------------------------------------------------------------
    # COLIN. edge case (line 157–158)
    # ------------------------------------------------------------------

    def test_colin_blank_lastname_edge_case(self):
        """Name with empty last name produces 'COLIN.' which is caught and fixed."""
        _, eh_id = correct_player_name("COLIN ", season=20162017)
        assert eh_id == "COLIN.WHITE2"

    # ------------------------------------------------------------------
    # Return type
    # ------------------------------------------------------------------

    def test_returns_tuple_of_two_strings(self):
        result = correct_player_name("FILIP FORSBERG", season=20232024)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(x, str) for x in result)


# ---------------------------------------------------------------------------
# Player class (network) — one fixture, shared across all tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def forsberg():
    return Player(player_id=8476887)  # Filip Forsberg


class TestPlayer:
    @pytest.mark.parametrize("backend", ["polars", "pandas"])
    def test_basic_instantiation(self, backend):
        player = Player(player_id=8476887, backend=backend)
        assert player.player_id == 8476887

    def test_identity(self, forsberg):
        assert forsberg.first_name == "Filip"
        assert forsberg.last_name == "Forsberg"
        assert forsberg.player_name == "Filip Forsberg"
        assert repr(forsberg) == "Player(player_id=8476887, backend='polars')"

    def test_seasons(self, forsberg):
        assert isinstance(forsberg.active_seasons, list) and len(forsberg.active_seasons) > 0
        assert isinstance(forsberg.playoff_seasons, list) and len(forsberg.playoff_seasons) > 0

    def test_career_stats(self, forsberg):
        forsberg._munge_career_regular_season_stats()
        stats = forsberg._career_regular_season_stats
        for key in ("games_played", "goals", "assists", "points"):
            assert key in stats

    def test_player_info(self, forsberg):
        assert isinstance(forsberg.player_info, dict) and len(forsberg.player_info) > 0

    def test_current_team(self, forsberg):
        assert isinstance(forsberg.is_active, bool)
        assert isinstance(forsberg.current_team_id, int)
        assert isinstance(forsberg.current_team, str) and len(forsberg.current_team) == 3
        assert isinstance(forsberg.current_team_name, str)
        assert isinstance(forsberg.current_team_full_name, str)
        assert isinstance(forsberg.current_team_full_name_fr, str)

    @pytest.mark.parametrize("player_id", [8471675, 8478402])  # Crosby, McDavid
    def test_other_players(self, player_id):
        player = Player(player_id=player_id)
        assert player.player_id == player_id
        assert isinstance(player.first_name, str)

    def test_prefetch_populates_cache(self, forsberg):
        forsberg.prefetch()
        assert "_landing_info" in forsberg.__dict__
        assert "_current_game_logs" in forsberg.__dict__

    def test_private_properties(self, forsberg):
        """Lines 172, 177, 192, 197, 202, 211: private data properties."""
        _ = forsberg._featured_regular_season_stats
        _ = forsberg._featured_career_stats
        _ = forsberg._career_playoff_stats
        _ = forsberg._last_five_games
        _ = forsberg._season_totals
        _ = forsberg._game_logs
