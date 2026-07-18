import pytest

from chickenstats.chicken_nhl.team import TEAM_COLORS, Team, alt_team_codes, team_codes, team_names
from chickenstats.exceptions import InvalidTeamError


# -----------------------------------------------------------------------------
# Data structure sanity checks
# -----------------------------------------------------------------------------


def test_team_codes_non_empty():
    assert len(team_codes) > 0


def test_team_names_non_empty():
    assert len(team_names) > 0


def test_team_codes_and_names_are_inverses():
    """Every value in team_codes should be a key in team_names."""
    for code in team_codes.values():
        assert code in team_names


def test_alt_team_codes_values_are_valid_codes():
    for code in alt_team_codes.values():
        assert code in team_names


def test_team_colors_keys_are_valid_codes():
    for code in TEAM_COLORS:
        assert code in team_names or code in alt_team_codes.values() or code == "ATL"


def test_team_colors_have_required_keys():
    for team, colors in TEAM_COLORS.items():
        assert "GOAL" in colors, f"{team} missing GOAL"
        assert "SHOT" in colors, f"{team} missing SHOT"
        assert "MISS" in colors, f"{team} missing MISS"


# -----------------------------------------------------------------------------
# Team.__init__ — team_code path
# -----------------------------------------------------------------------------


class TestTeam:
    def test_basic_construction(self):
        team = Team(team_code="NSH")
        assert team.team_code == "NSH"

    def test_team_name_resolved(self):
        team = Team(team_code="NSH")
        assert team.team_name == "NASHVILLE PREDATORS"

    def test_team_code_alt_set(self):
        team = Team(team_code="NSH")
        assert team.team_code_alt == "NSH"

    def test_colors_dict_populated(self):
        team = Team(team_code="NSH")
        assert isinstance(team.colors, dict)
        assert "GOAL" in team.colors
        assert "SHOT" in team.colors
        assert "MISS" in team.colors

    def test_colors_primary_secondary_tertiary(self):
        team = Team(team_code="NSH")
        assert team.primary_color == team.colors["GOAL"]
        assert team.secondary_color == team.colors["SHOT"]
        assert team.tertiary_color == team.colors["MISS"]

    def test_logo_url_contains_team_code(self):
        team = Team(team_code="NSH")
        assert "NSH" in team.logo_url
        assert team.logo_url.endswith(".png")

    # -----------------------------------------------------------------------------
    # Alternate team code resolution
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "alt_code,expected_code", [("L.A", "LAK"), ("N.J", "NJD"), ("S.J", "SJS"), ("T.B", "TBL"), ("PHX", "ARI")]
    )
    def test_alt_team_code(self, alt_code, expected_code):
        team = Team(team_code=alt_code)
        assert team.team_code == expected_code
        assert team.team_code_alt == alt_code

    # -----------------------------------------------------------------------------
    # ARI — alt colors
    # -----------------------------------------------------------------------------

    def test_ari_has_alt_colors(self):
        team = Team(team_code="ARI")
        assert hasattr(team, "colors_alt")
        assert "GOAL" in team.colors_alt

    def test_ari_primary_color_alt(self):
        team = Team(team_code="ARI")
        assert team.primary_color_alt == team.colors_alt["GOAL"]

    # -----------------------------------------------------------------------------
    # International teams
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize("code", ["CAN", "FIN", "SWE", "USA"])
    def test_international_team(self, code):
        team = Team(team_code=code)
        assert team.team_code == code
        assert isinstance(team.colors, dict)
        assert "international" in team.logo_url

    # -----------------------------------------------------------------------------
    # Validation errors
    # -----------------------------------------------------------------------------

    def test_no_args_raises(self):
        with pytest.raises(InvalidTeamError):
            Team()

    def test_invalid_team_code_raises(self):
        with pytest.raises(InvalidTeamError):
            Team(team_code="INVALID")

    def test_invalid_team_name_raises(self):
        with pytest.raises(InvalidTeamError):
            Team(team_name="INVALID TEAM NAME")

    # -----------------------------------------------------------------------------
    # Case-insensitivity
    # -----------------------------------------------------------------------------

    def test_lowercase_team_code_resolves(self):
        team = Team(team_code="nsh")
        assert team.team_code == "NSH"

    def test_mixed_case_team_code_resolves(self):
        team = Team(team_code="NsH")
        assert team.team_code == "NSH"

    def test_lowercase_team_name_resolves(self):
        team = Team(team_name="nashville predators")
        assert team.team_code == "NSH"

    def test_lowercase_alt_team_code_resolves(self):
        team = Team(team_code="l.a")
        assert team.team_code == "LAK"

    # -----------------------------------------------------------------------------
    # Fuzzy-match suggestions in error messages
    # -----------------------------------------------------------------------------

    def test_invalid_team_code_suggests_close_match(self):
        with pytest.raises(InvalidTeamError, match="NSH"):
            Team(team_code="NSJ")

    def test_invalid_team_name_suggests_close_match(self):
        with pytest.raises(InvalidTeamError, match="NASHVILLE PREDATORS"):
            Team(team_name="NASHVILE PREDATORS")

    def test_no_suggestion_when_no_close_match(self):
        """A team code with no reasonably close match doesn't fabricate a suggestion."""
        with pytest.raises(InvalidTeamError) as exc_info:
            Team(team_code="ZZZ")
        assert "Did you mean" not in str(exc_info.value)

    # -----------------------------------------------------------------------------
    # team_name-only construction
    # -----------------------------------------------------------------------------

    def test_team_name_only_construction(self):
        team = Team(team_name="NASHVILLE PREDATORS")
        assert team.team_code == "NSH"
        assert team.team_name == "NASHVILLE PREDATORS"
        assert isinstance(team.colors, dict)

    def test_team_name_only_code_alt_equals_code(self):
        """When constructed from team_name, team_code_alt matches team_code."""
        team = Team(team_name="NASHVILLE PREDATORS")
        assert team.team_code_alt == team.team_code

    # -----------------------------------------------------------------------------
    # Historical team — no TEAM_COLORS entry (fallback palette)
    # -----------------------------------------------------------------------------

    def test_historical_team_no_colors_uses_fallback(self):
        """Teams absent from TEAM_COLORS get the fallback color palette."""
        team = Team(team_code="BRK")  # Brooklyn Americans — not in TEAM_COLORS
        assert isinstance(team.colors, dict)
        assert "GOAL" in team.colors
        assert "SHOT" in team.colors
        assert "MISS" in team.colors

    # -----------------------------------------------------------------------------
    # logo property (network)
    # -----------------------------------------------------------------------------

    def test_logo_returns_image(self):
        from PIL import Image

        team = Team(team_code="NSH")
        assert isinstance(team.logo, Image.Image)

    def test_logo_is_cached(self):
        """logo is a cached_property — repeated access shouldn't re-download."""
        team = Team(team_code="NSH")
        first = team.logo
        assert "logo" in team.__dict__
        assert team.logo is first

    def test_logo_raises_clear_error_on_http_error(self):
        """A non-2xx response must surface as a clear requests.HTTPError from
        raise_for_status(), not an opaque error deep in image decoding."""
        import requests
        from unittest.mock import MagicMock, patch

        team = Team(team_code="NSH")
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
        with patch.object(team._requests_session, "get", return_value=mock_response):
            with pytest.raises(requests.exceptions.HTTPError):
                _ = team.logo
