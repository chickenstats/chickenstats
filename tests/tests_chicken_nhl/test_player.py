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
# Player class (network)
# ---------------------------------------------------------------------------


class TestPlayer:
    @pytest.mark.parametrize("backend", ["polars", "pandas"])
    def test_basic_instantiation(self, backend):
        player = Player(player_id=8476887, backend=backend)  # Filip Forsberg
        assert player.player_id == 8476887

    def test_player_name(self):
        player = Player(player_id=8476887)
        assert player.first_name == "Filip"
        assert player.last_name == "Forsberg"

    def test_active_seasons_non_empty(self):
        player = Player(player_id=8476887)
        assert isinstance(player.active_seasons, list)
        assert len(player.active_seasons) > 0

    def test_career_stats_munged(self):
        player = Player(player_id=8476887)
        player._munge_career_regular_season_stats()
        stats = player._career_regular_season_stats
        assert "games_played" in stats
        assert "goals" in stats
        assert "assists" in stats
        assert "points" in stats

    def test_player_info_populated(self):
        player = Player(player_id=8476887)
        assert isinstance(player.player_info, dict)
        assert len(player.player_info) > 0

    @pytest.mark.parametrize("player_id", [8471675, 8478402])  # Crosby, McDavid
    def test_multiple_players(self, player_id):
        player = Player(player_id=player_id)
        assert player.player_id == player_id
        assert isinstance(player.first_name, str)
        assert isinstance(player.last_name, str)

    def test_repr(self):
        player = Player(player_id=8476887)
        assert repr(player) == "Player(player_id=8476887, backend='polars')"

    def test_player_name_property(self):
        player = Player(player_id=8476887)
        assert player.player_name == f"{player.first_name} {player.last_name}"

    def test_is_active(self):
        player = Player(player_id=8476887)
        assert isinstance(player.is_active, bool)

    def test_current_team_id(self):
        player = Player(player_id=8476887)
        assert isinstance(player.current_team_id, int)

    def test_current_team(self):
        player = Player(player_id=8476887)
        assert isinstance(player.current_team, str)
        assert len(player.current_team) == 3

    def test_current_team_name(self):
        player = Player(player_id=8476887)
        assert isinstance(player.current_team_name, str)

    def test_current_team_full_name(self):
        player = Player(player_id=8476887)
        assert isinstance(player.current_team_full_name, str)

    def test_current_team_full_name_fr(self):
        player = Player(player_id=8476887)
        assert isinstance(player.current_team_full_name_fr, str)

    def test_playoff_seasons(self):
        player = Player(player_id=8476887)  # Forsberg has playoff appearances
        assert isinstance(player.playoff_seasons, list)
        assert len(player.playoff_seasons) > 0

    def test_prefetch_populates_cache(self):
        player = Player(player_id=8476887)
        player.prefetch()
        assert "_landing_info" in player.__dict__
        assert "_current_game_logs" in player.__dict__
