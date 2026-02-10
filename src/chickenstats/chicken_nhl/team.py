from io import BytesIO
from PIL import Image, ImageFile

from chickenstats.utilities import ChickenSession
from chickenstats.chicken_nhl._info import NHL_COLORS, team_names, alt_team_codes, team_codes, INTERNATIONAL_COLORS


class Team:
    """Class instance for team information, including team name, code, and colors.

    Parameters:
        team_code (str | None):
            Three-letter team code, e.g., NSH
        team_name: (str | None):
            Team's full name, e.g., NASHVILLE PREDATORS

    Attributes:
        team_code (str):
            Three-letter team code, e.g., NSH
        team_code_alt (str):
            Alternate team code, if it exists e.g., T.B. vs. TBL, PHX vs. ARI
        team_name (str):
            Full team name, e.g., NASHVILLE PREDATORS
        colors (dict):
            Dictionary of team colors, to be used in charts. Primary and secondary colors
            are mapped to "GOAL" and "SHOT", respectively. "MISS" is a gray used for everyone
        primary_color (str):
            Team's primary color, also mapped to self.colors["GOAL"]
        secondary_color (str):
            Team's secondary color, also mapped to self.colors["SHOT"]
        tertiary_color (str):
            Gray used for eall teams, also mapped to self.colors["MISS"]
        logo_url (str):
            URL to download logo from chickenstats GitHub repo.

    Examples:
        Get team colors as a dictionary:
        >>> from chickenstats.chicken_nhl import Team
        >>> team = Team(team_code="NSH")
        >>> team.colors

        Get team logo as an ImageFile:
        >>> from chickenstats.chicken_nhl import Team
        >>> team = Team(team_code="NASHVILLE PREDATORS")
        >>> team.logo
    """

    def __init__(self, team_code: str | None = None, team_name: str | None = None) -> None:
        """Instantiates team information, including team name, code, and colors."""
        if not team_code and not team_name:
            raise ValueError("Either team code or team name must be provided.")

        if team_code and team_code not in team_names.keys() and team_codes not in alt_team_codes.keys():
            raise ValueError(f"Team code {team_code} is not valid.")

        if team_name and team_name not in team_codes.keys():
            raise ValueError(f"Team name {team_name} is not valid.")

        if not team_code:
            team_code = team_codes[team_name]

        if not team_name:
            team_code_alt = f"{team_code}"

            if team_code in alt_team_codes.keys():
                team_code = alt_team_codes[team_code]

            team_name = team_names[team_code]

        self.team_code = team_code
        self.team_code_alt = team_code_alt
        self.team_name = team_name

        if team_code in NHL_COLORS.keys():
            self.colors = NHL_COLORS[team_code]
            folder_stem = "nhl"

        elif team_code in INTERNATIONAL_COLORS.keys():
            self.colors = INTERNATIONAL_COLORS[team_code]
            folder_stem = "international"

        self.primary_color = self.colors["GOAL"]
        self.secondary_color = self.colors["SHOT"]
        self.tertiary_color = self.colors["MISS"]

        if team_code == "ARI":
            self.colors_alt = {"GOAL": "#E2D6B5", "SHOT": "#8C2633", "MISS": "#D3D3D3"}
            self.primary_color_alt = self.colors_alt["GOAL"]
            self.secondary_color_alt = self.colors_alt["SHOT"]
            self.tertiary_color_alt = self.colors_alt["MISS"]

        url_stem = "https://raw.githubusercontent.com/chickenandstats/chickenstats/refs/heads/main/logos"
        self.logo_url = f"{url_stem}/{folder_stem}/{team_code}.png"

    @property
    def logo(self) -> ImageFile.ImageFile:
        """Fetch logo from chickenstats GitHub repo.

        Returns logo as an ImageFile

        Examples:
            >>> from chickenstats.chicken_nhl import Team
            >>> team = Team(team_code="NSH")
            >>> team.logo

        """
        with ChickenSession() as session:
            logo = BytesIO(session.get(self.logo_url).content)

            logo = Image.open(logo)

            return logo
