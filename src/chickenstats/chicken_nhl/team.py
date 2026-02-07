from io import BytesIO
from PIL import Image, ImageFile

from chickenstats.utilities import ChickenSession
from chickenstats.chicken_nhl import Season
from chickenstats.chicken_nhl._info import NHL_COLORS, team_names, alt_team_codes, team_codes, INTERNATIONAL_COLORS

import pandas as pd
import polars as pl

from typing import Literal


class Team:
    """Class instance for team information, including team name, code, and colors."""

    def __init__(
        self,
        team_code: str | None = None,
        team_name: str | None = None,
        backend: Literal["polars", "pandas"] = "polars",
    ) -> None:
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

        self._game_ids: list | None = None

    @property
    def logo(self) -> ImageFile.ImageFile:
        """Fetch logo from chickenstats GitHub repo."""
        with ChickenSession() as session:
            logo = BytesIO(session.get(self.logo_url).content)

            logo = Image.open(logo)

            return logo
