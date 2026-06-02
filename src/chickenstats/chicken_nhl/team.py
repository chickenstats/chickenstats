"""Team identity data: color maps, code lookups, and the Team utility class.

Module-level constants:
    team_codes: dict mapping uppercase full team names to their 3-letter NHL codes.
    team_names: dict mapping 3-letter codes to full team display names.
    alt_team_codes: dict mapping alternate/historical codes to current codes.
    TEAM_COLORS: dict mapping team codes to goal/shot/miss hex color triplets.
    _INTERNATIONAL_CODES: frozenset of non-NHL (international/all-star) codes
        excluded from standard team lookups.

Public class:
    Team: Resolves a team code or name to its canonical identity and colors.
"""

from __future__ import annotations

from io import BytesIO
from PIL import Image, ImageFile

from chickenstats.exceptions import InvalidTeamError
from chickenstats.utilities import ChickenSession

# Maps uppercase full team names (e.g. "TORONTO MAPLE LEAFS") → 3-letter NHL code.
# Used in Team.__init__ to resolve name-based lookups. Includes active franchises,
# relocated/defunct teams, and international codes.
team_codes = {
    "ANAHEIM DUCKS": "ANA",
    "ARIZONA COYOTES": "ARI",
    "ATLANTA FLAMES": "AFM",
    "ATLANTA THRASHERS": "ATL",
    "BOSTON BRUINS": "BOS",
    "BROOKLYN AMERICANS": "BRK",
    "BUFFALO SABRES": "BUF",
    "CALGARY FLAMES": "CGY",
    "CALGARY TIGERS": "CAT",
    "CALIFORNIA GOLDEN SEALS": "CGS",
    "CANADA": "CAN",
    "CAROLINA HURRICANES": "CAR",
    "CHICAGO BLACKHAWKS": "CHI",
    "CLEVELAND BARONS": "CLE",
    "COLORADO AVALANCHE": "COL",
    "COLORADO ROCKIES": "CLR",
    "COLUMBUS BLUE JACKETS": "CBJ",
    "DALLAS STARS": "DAL",
    "DETROIT COUGARS": "DCG",
    "DETROIT FALCONS": "DFL",
    "DETROIT RED WINGS": "DET",
    "EDMONTON ESKIMOS": "EDE",
    "EDMONTON OILERS": "EDM",
    "FINLAND": "FIN",
    "FLORIDA PANTHERS": "FLA",
    "HAMILTON TIGERS": "HAM",
    "HARTFORD WHALERS": "HFD",
    "KANSAS CITY SCOUTS": "KCS",
    "LOS ANGELES KINGS": "LAK",
    "MINNESOTA NORTH STARS": "MNS",
    "MINNESOTA WILD": "MIN",
    "MONTREAL CANADIENS": "MTL",
    "MONTREAL MAROONS": "MMR",
    "MONTREAL WANDERERS": "MWN",
    "NASHVILLE PREDATORS": "NSH",
    "NEW JERSEY DEVILS": "NJD",
    "NEW YORK AMERICANS": "NYA",
    "NEW YORK ISLANDERS": "NYI",
    "NEW YORK RANGERS": "NYR",
    "OAKLAND SEALS": "OAK",
    "OTTAWA SENATORS": "OTT",
    "OTTAWA SENATORS (1917)": "SEN",
    "PHILADELPHIA FLYERS": "PHI",
    "PHILADELPHIA QUAKERS": "QUA",
    "PITTSBURGH PENGUINS": "PIT",
    "PITTSBURGH PIRATES": "PIR",
    "QUEBEC BULLDOGS": "QBD",
    "QUEBEC NORDIQUES": "QUE",
    "SAN JOSE SHARKS": "SJS",
    "SEATTLE KRAKEN": "SEA",
    "SEATTLE METROPOLITANS": "SEA",
    "ST. LOUIS BLUES": "STL",
    "ST. LOUIS EAGLES": "SLE",
    "SWEDEN": "SWE",
    "TAMPA BAY LIGHTNING": "TBL",
    "TORONTO ARENAS": "TAN",
    "TORONTO MAPLE LEAFS": "TOR",
    "TORONTO ST. PATRICKS": "TSP",
    "UNITED STATES": "USA",
    "UTAH HOCKEY CLUB": "UTA",
    "UTAH MAMMOTH": "UTA",
    "VANCOUVER CANUCKS": "VAN",
    "VANCOUVER MAROONS": "VMA",
    "VANCOUVER MILLIONAIRES": "VMI",
    "VEGAS GOLDEN KNIGHTS": "VGK",
    "VICTORIA COUGARS": "VIC",
    "WASHINGTON CAPITALS": "WSH",
    "WINNIPEG JETS": "WPG",
    "WINNIPEG JETS (1979)": "WIN",
}

# Reverse of team_codes: maps 3-letter NHL code → uppercase full team display name
# (e.g. "TOR" → "TORONTO MAPLE LEAFS"). Used in Team.__init__ to resolve code-based lookups.
team_names = {
    "ANA": "ANAHEIM DUCKS",
    "ARI": "ARIZONA COYOTES",
    "AFM": "ATLANTA FLAMES",
    "ATL": "ATLANTA THRASHERS",
    "BOS": "BOSTON BRUINS",
    "BRK": "BROOKLYN AMERICANS",
    "BUF": "BUFFALO SABRES",
    "CAN": "CANADA",
    "CGY": "CALGARY FLAMES",
    "CAT": "CALGARY TIGERS",
    "CGS": "CALIFORNIA GOLDEN SEALS",
    "CAR": "CAROLINA HURRICANES",
    "CHI": "CHICAGO BLACKHAWKS",
    "CLE": "CLEVELAND BARONS",
    "COL": "COLORADO AVALANCHE",
    "CLR": "COLORADO ROCKIES",
    "CBJ": "COLUMBUS BLUE JACKETS",
    "DAL": "DALLAS STARS",
    "DCG": "DETROIT COUGARS",
    "DFL": "DETROIT FALCONS",
    "DET": "DETROIT RED WINGS",
    "EDE": "EDMONTON ESKIMOS",
    "EDM": "EDMONTON OILERS",
    "FIN": "FINLAND",
    "FLA": "FLORIDA PANTHERS",
    "HAM": "HAMILTON TIGERS",
    "HFD": "HARTFORD WHALERS",
    "KCS": "KANSAS CITY SCOUTS",
    "LAK": "LOS ANGELES KINGS",
    "MNS": "MINNESOTA NORTH STARS",
    "MIN": "MINNESOTA WILD",
    "MTL": "MONTREAL CANADIENS",
    "MMR": "MONTREAL MAROONS",
    "MWN": "MONTREAL WANDERERS",
    "NSH": "NASHVILLE PREDATORS",
    "NJD": "NEW JERSEY DEVILS",
    "NYA": "NEW YORK AMERICANS",
    "NYI": "NEW YORK ISLANDERS",
    "NYR": "NEW YORK RANGERS",
    "OAK": "OAKLAND SEALS",
    "OTT": "OTTAWA SENATORS",
    "SEN": "OTTAWA SENATORS (1917)",
    "PHI": "PHILADELPHIA FLYERS",
    "QUA": "PHILADELPHIA QUAKERS",
    "PIT": "PITTSBURGH PENGUINS",
    "PIR": "PITTSBURGH PIRATES",
    "QBD": "QUEBEC BULLDOGS",
    "QUE": "QUEBEC NORDIQUES",
    "SJS": "SAN JOSE SHARKS",
    "SEA": "SEATTLE KRAKEN",
    "STL": "ST. LOUIS BLUES",
    "SLE": "ST. LOUIS EAGLES",
    "SWE": "SWEDEN",
    "TBL": "TAMPA BAY LIGHTNING",
    "TAN": "TORONTO ARENAS",
    "TOR": "TORONTO MAPLE LEAFS",
    "TSP": "TORONTO ST. PATRICKS",
    "USA": "UNITED STATES",
    "UTA": "UTAH MAMMOTH",
    "VAN": "VANCOUVER CANUCKS",
    "VMA": "VANCOUVER MAROONS",
    "VMI": "VANCOUVER MILLIONAIRES",
    "VGK": "VEGAS GOLDEN KNIGHTS",
    "VIC": "VICTORIA COUGARS",
    "WSH": "WASHINGTON CAPITALS",
    "WPG": "WINNIPEG JETS",
    "WIN": "WINNIPEG JETS (1979)",
}

# Maps alternate or historical team codes to their current canonical 3-letter code.
# Covers dot-separated API variants (e.g. "L.A" → "LAK") and relocated franchises
# (e.g. "PHX" → "ARI" for the former Phoenix Coyotes). Checked in Team.__init__ when
# the input code does not match team_names directly.
alt_team_codes = {"L.A": "LAK", "N.J": "NJD", "S.J": "SJS", "T.B": "TBL", "PHX": "ARI"}

# Per-team chart color triplets: {"GOAL": hex, "SHOT": hex, "MISS": hex}.
# GOAL = primary accent color for goals, SHOT = secondary color for shots on goal,
# MISS = neutral grey for missed shots. Assigned to self.colors in Team.__init__.
# Historical/defunct teams are included so archived game data renders correctly.
TEAM_COLORS = {
    # NHL teams
    "ANA": {"GOAL": "#F47A38", "SHOT": "#000000", "MISS": "#D3D3D3"},
    "ATL": {"GOAL": "#5C88DA", "SHOT": "#041E42", "MISS": "#D3D3D3"},
    # Former Arizona Coyotes colors — now surfaced as Team.colors_alt for the Utah Hockey Club entry
    # 'ARI': {'GOAL': '#E2D6B5', 'SHOT': '#8C2633', 'MISS': '#D3D3D3'},
    "ARI": {"GOAL": "#A9431E", "SHOT": "#5F259F", "MISS": "#D3D3D3"},
    "BOS": {"GOAL": "#FFB81C", "SHOT": "#000000", "MISS": "#D3D3D3"},
    "BUF": {"GOAL": "#FCB514", "SHOT": "#002654", "MISS": "#D3D3D3"},
    "CAR": {"GOAL": "#CC0000", "SHOT": "#000000", "MISS": "#D3D3D3"},
    "CBJ": {"GOAL": "#CE1126", "SHOT": "#002654", "MISS": "#D3D3D3"},
    "CGY": {"GOAL": "#F1BE48", "SHOT": "#C8102E", "MISS": "#D3D3D3"},
    "CHI": {"GOAL": "#CF0A2C", "SHOT": "#000000", "MISS": "#D3D3D3"},
    "COL": {"GOAL": "#236192", "SHOT": "#6F263D", "MISS": "#D3D3D3"},
    "DAL": {"GOAL": "#006847", "SHOT": "#111111", "MISS": "#D3D3D3"},
    "DET": {"GOAL": "#FFFFFF", "SHOT": "#CE1126", "MISS": "#D3D3D3"},
    "EDM": {"GOAL": "#FF4C00", "SHOT": "#041E42", "MISS": "#D3D3D3"},
    "FLA": {"GOAL": "#C8102E", "SHOT": "#041E42", "MISS": "#D3D3D3"},
    "LAK": {"GOAL": "#A2AAAD", "SHOT": "#111111", "MISS": "#D3D3D3"},
    "MIN": {"GOAL": "#A6192E", "SHOT": "#154734", "MISS": "#D3D3D3"},
    "MTL": {"GOAL": "#AF1E2D", "SHOT": "#192168", "MISS": "#D3D3D3"},
    "NJD": {"GOAL": "#CE1126", "SHOT": "#000000", "MISS": "#D3D3D3"},
    "NSH": {"GOAL": "#FFB81C", "SHOT": "#041E42", "MISS": "#D3D3D3"},
    "NYI": {"GOAL": "#F47D30", "SHOT": "#00539B", "MISS": "#D3D3D3"},
    "NYR": {"GOAL": "#CE1126", "SHOT": "#0038A8", "MISS": "#D3D3D3"},
    "OTT": {"GOAL": "#C2912C", "SHOT": "#C52032", "MISS": "#D3D3D3"},
    "PHI": {"GOAL": "#F74902", "SHOT": "#000000", "MISS": "#D3D3D3"},
    "PIT": {"GOAL": "#FCB514", "SHOT": "#000000", "MISS": "#D3D3D3"},
    "SEA": {"GOAL": "#99D9D9", "SHOT": "#001628", "MISS": "#D3D3D3"},
    "SJS": {"GOAL": "#006D75", "SHOT": "#000000", "MISS": "#D3D3D3"},
    "STL": {"GOAL": "#FCB514", "SHOT": "#002F87", "MISS": "#D3D3D3"},
    "TBL": {"GOAL": "#FFFFFF", "SHOT": "#002868", "MISS": "#D3D3D3"},
    "TOR": {"GOAL": "#FFFFFF", "SHOT": "#00205B", "MISS": "#D3D3D3"},
    "UTA": {"GOAL": "#6CACE4", "SHOT": "#010101", "MISS": "#D3D3D3"},
    "VAN": {"GOAL": "#00843D", "SHOT": "#00205B", "MISS": "#D3D3D3"},
    "VGK": {"GOAL": "#B4975A", "SHOT": "#333F42", "MISS": "#D3D3D3"},
    "WSH": {"GOAL": "#C8102E", "SHOT": "#041E42", "MISS": "#D3D3D3"},
    "WPG": {"GOAL": "#AC162C", "SHOT": "#041E42", "MISS": "#D3D3D3"},
    # International teams
    "CAN": {"GOAL": "#CC3333", "SHOT": "#000000", "MISS": "#D3D3D3"},
    "FIN": {"GOAL": "#FBBF16", "SHOT": "#0F80CC", "MISS": "#D3D3D3"},
    "SWE": {"GOAL": "#FCD116", "SHOT": "#3063AE", "MISS": "#D3D3D3"},
    "USA": {"GOAL": "#BB2533", "SHOT": "#1F2742", "MISS": "#D3D3D3"},
}

# Non-NHL codes recognized by the library for international and all-star games.
# Used in Team.__init__ to route logo fetches to the "international" folder instead
# of "nhl". Prefixed _ because callers should use Team; direct access is an
# implementation detail.
_INTERNATIONAL_CODES: frozenset[str] = frozenset({"CAN", "FIN", "SWE", "USA"})


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
            Gray used for all teams, also mapped to self.colors["MISS"]
        logo_url (str):
            URL to download logo from chickenstats GitHub repo.

    Examples:
        Get team colors as a dictionary:
        >>> from chickenstats.chicken_nhl import Team
        >>> team = Team(team_code="NSH")
        >>> team.colors

        Get team logo as an ImageFile:
        >>> from chickenstats.chicken_nhl import Team
        >>> team = Team(team_name="NASHVILLE PREDATORS")
        >>> team.logo
    """

    def __init__(self, team_code: str | None = None, team_name: str | None = None) -> None:
        """Instantiates team information, including team name, code, and colors."""
        if not team_code and not team_name:
            raise InvalidTeamError("Either team code or team name must be provided.")

        if team_code and team_code not in team_names and team_code not in alt_team_codes:
            raise InvalidTeamError(f"Team code {team_code!r} is not valid.")

        if team_name and team_name not in team_codes:
            raise InvalidTeamError(f"Team name {team_name!r} is not valid.")

        if not team_code:
            team_code = team_codes[team_name]  # ty: ignore[invalid-argument-type]

        # Preserve the original input code before alt-code resolution
        team_code_alt = team_code

        if team_code in alt_team_codes:
            team_code = alt_team_codes[team_code]

        if not team_name:
            team_name = team_names[team_code]

        self.team_code = team_code
        self.team_code_alt = team_code_alt
        self.team_name = team_name

        self.colors = TEAM_COLORS.get(team_code, {"GOAL": "#000000", "SHOT": "#808080", "MISS": "#D3D3D3"})
        folder_stem = "international" if team_code in _INTERNATIONAL_CODES else "nhl"

        self.primary_color = self.colors["GOAL"]
        self.secondary_color = self.colors["SHOT"]
        self.tertiary_color = self.colors["MISS"]

        if team_code == "ARI":
            self.colors_alt = {"GOAL": "#E2D6B5", "SHOT": "#8C2633", "MISS": "#D3D3D3"}
            self.primary_color_alt = self.colors_alt["GOAL"]
            self.secondary_color_alt = self.colors_alt["SHOT"]
            self.tertiary_color_alt = self.colors_alt["MISS"]

        url_stem = "https://raw.githubusercontent.com/chickenandstats/chickenstats/refs/heads/main/assets/logos"
        self.logo_url = f"{url_stem}/{folder_stem}/{team_code}.png"

    def __repr__(self) -> str:
        """Return string representation of Team object."""
        return f"Team(team_code={self.team_code!r}, team_name={self.team_name!r})"

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
