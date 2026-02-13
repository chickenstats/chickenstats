from typing import Literal

from chickenstats.utilities import ChickenSession

from unidecode import unidecode

correct_names_dict = {
    "AJ GREER": "A.J. GREER",
    "ALEXEY TOROPCHENKO": "ALEXEI TOROPCHENKO",
    "ANDR BENOT": "ANDRE BENOIT",
    "ANTHONY DEANGELO": "TONY DEANGELO",
    "BJ CROMBEEN": "B.J. CROMBEEN",
    "BO GROULX": "BENOIT-OLIVIER GROULX",
    "BRADLEY MILLS": "BRAD MILLS",
    "CAL PETERSEN": "CALVIN PETERSEN",
    "CALLAN FOOTE": "CAL FOOTE",
    "CAM HILLIS": "CAMERON HILLIS",
    "CHASE DELEO": "CHASE DE LEO",
    "CHRIS VANDE VELDE": "CHRIS VANDEVELDE",
    "CRISTOVAL NIEVES": "BOO NIEVES",
    "DAN CLEARY": "DANIEL CLEARY",
    "DANNY CLEARY": "DANIEL CLEARY",
    "DANIEL CARCILLO": "DAN CARCILLO",
    "DANNY BRIERE": "DANIEL BRIERE",
    "DANNY O'REGAN": "DANIEL O'REGAN",
    "DAVID JOHNNY ODUYA": "JOHNNY ODUYA",
    "EVGENII DADONOV": "EVGENY DADONOV",
    "EGOR SHARANGOVICH": "YEGOR SHARANGOVICH",
    "FREDDY MODIN": "FREDRIK MODIN",
    "FREDERICK MEYER IV": "FREDDY MEYER",
    "GERRY MAYHEW": "GERALD MAYHEW",
    "HARRISON ZOLNIERCZYK": "HARRY ZOLNIERCZYK",
    "JAMES WYMAN": "J.T. WYMAN",
    "JT WYMAN": "J.T. WYMAN",
    "JEAN-FRANCOIS BERUBE": "J-F BERUBE",
    "J.F. BERUBE": "J-F BERUBE",
    "J.J. MOSER": "JANIS MOSER",
    "JAKE MIDDLETON": "JACOB MIDDLETON",
    "JEAN-FRANCOIS JACQUES": "J-F JACQUES",
    "JONATHAN AUDY-MARCHESSAULT": "JONATHAN MARCHESSAULT",
    "JOSH DUNNE": "JOSHUA DUNNE",
    "JOSHUA MORRISSEY": "JOSH MORRISSEY",
    "JT BROWN": "J.T. BROWN",
    "JT COMPHER": "J.T. COMPHER",
    "KENNETH APPLEBY": "KEN APPLEBY",
    "KRYSTOFER BARCH": "KRYS BARCH",
    "MARTIN ST LOUIS": "MARTIN ST. LOUIS",
    "MARTIN ST PIERRE": "MARTIN ST. PIERRE",
    "MARTY HAVLAT": "MARTIN HAVLAT",
    "MATHEW DUMBA": "MATT DUMBA",
    "MATTHEW DUMBA": "MATT DUMBA",
    "MATTHEW BENNING": "MATT BENNING",
    "MATTHEW CARLE": "MATT CARLE",
    "MATTHEW IRWIN": "MATT IRWIN",
    "MATTHEW MURRAY": "MATT MURRAY",
    "MATTHEW NIETO": "MATT NIETO",
    "MATTIAS JANMARK-NYLEN": "MATTIAS JANMARK",
    "MAXIME TALBOT": "MAX TALBOT",
    "MAX LAJOIE": "MAXIME LAJOIE",
    "MAXWELL REINHART": "MAX REINHART",
    "MICHAEL CAMMALLERI": "MIKE CAMMALLERI",
    "MICHAEL GRIER": "MIKE GRIER",
    "MICHAEL FERLAND": "MICHEAL FERLAND",
    "MICHAEL MATHESON": "MIKE MATHESON",
    "MICHAEL RUPP": "MIKE RUPP",
    "MICHAEL SANTORELLI": "MIKE SANTORELLI",
    "MICHAEL YORK": "MIKE YORK",
    "MIKE ZIGOMANIS": "MICHAEL ZIGOMANIS",
    "MIKE VERNACE": "MICHAEL VERNACE",
    "MITCHELL MARNER": "MITCH MARNER",
    "NICOLAS PETAN": "NIC PETAN",
    "NICHOLAS BAPTISTE": "NICK BAPTISTE",
    "NICHOLAS BOYNTON": "NICK BOYNTON",
    "NICHOLAS CAAMANO": "NICK CAAMANO",
    "NICHOLAS DRAZENOVIC": "NICK DRAZENOVIC",
    "NICHOLAS PAUL": "NICK PAUL",
    "NICHOLAS SHORE": "NICK SHORE",
    "NICK ABRUZZESE": "NICHOLAS ABRUZZESE",
    "NICK MERKLEY": "NICHOLAS MERKLEY",
    "NICKLAS GROSSMAN": "NICKLAS GROSSMANN",
    "NIKLAS KRONVALL": "NIKLAS KRONWALL",
    "NIKOLAI KULEMIN": "NIKOLAY KULEMIN",
    "OLIVIER MAGNAN-GRENIER": "OLIVIER MAGNAN",
    "PA PARENTEAU": "P.A. PARENTEAU",
    "PIERRE-ALEX PARENTEAU": "P.A. PARENTEAU",
    "PAT MAROON": "PATRICK MAROON",
    "PHILIP VARONE": "PHIL VARONE",
    "QUINTIN HUGHES": "QUINN HUGHES",
    "RJ UMBERGER": "R.J. UMBERGER",
    "SAMMY WALKER": "SAMUEL WALKER",
    "SASHA CHMELEVSKI": "ALEX CHMELEVSKI",
    "STEVEN REINPRECHT": "STEVE REINPRECHT",
    "THOMAS MCCOLLUM": "TOM MCCOLLUM",
    "TIM GETTINGER": "TIMOTHY GETTINGER",
    "TJ GALIARDI": "T.J. GALIARDI",
    "TJ HENSICK": "T.J. HENSICK",
    "TJ OSHIE": "T.J. OSHIE",
    "TJ TYNAN": "T.J. TYNAN",
    "TOBY ENSTROM": "TOBIAS ENSTROM",
    "TOMMY NOVAK": "THOMAS NOVAK",  # API ID: 8478438
    "VINCENT HINOSTROZA": "VINNIE HINOSTROZA",
    "WILL BORGEN": "WILLIAM BORGEN",
    "WILLIAM THOMAS": "BILL THOMAS",
    "ZACHARY ASTON-REESE": "ZACH ASTON-REESE",
    "ZACHARY HAYES": "ZACK HAYES",
    "ZACHARY SANFORD": "ZACH SANFORD",
}

correct_api_names_dict = {
    8480222: "SEBASTIAN.AHO2",
    8476979: "ERIK.GUSTAFSSON2",
    8478400: "COLIN.WHITE2",
    8474744: "SEAN.COLLINS2",
    8471221: "ALEX.PICARD2",
    8482247: "MIKKO.LEHTONEN2",
    8480979: "NATHAN.SMITH2",
    8480193: "DANIIL.TARASOV2",
    8483678: "ELIAS.PETTERSSON2",
}


def correct_player_name(
    player_name: str, season: str | int, player_position: str = None, player_jersey: str | int = None
) -> tuple[str, str]:
    """Docstring."""
    player_name = player_name.replace("ALEXANDRE", "ALEX").replace("ALEXANDER", "ALEX").replace("CHRISTOPHER", "CHRIS")

    player_name = correct_names_dict.get(player_name, player_name)

    player_eh_id = unidecode(player_name)
    name_split = player_eh_id.split(" ", maxsplit=1)

    player_eh_id = f"{name_split[0]}.{name_split[1]}".replace("..", ".")

    # Correcting Evolving Hockey IDs for duplicates

    duplicates = {
        "SEBASTIAN.AHO": player_position == "D",
        "COLIN.WHITE": season >= 20162017,
        "SEAN.COLLINS": player_position is not None and player_position != "D",
        "ALEX.PICARD": player_position is not None and player_position != "D",
        "ERIK.GUSTAFSSON": season >= 20152016,
        "MIKKO.LEHTONEN": season >= 20202021,
        "NATHAN.SMITH": season >= 20212022,
        "DANIIL.TARASOV": player_position == "G",
        "ELIAS.PETTERSSON": player_position == "D" or player_jersey == "VAN25" or player_jersey == 25,
    }

    # Iterating through the duplicate names and conditions

    for duplicate_name, condition in duplicates.items():
        if player_eh_id == duplicate_name and condition:
            player_eh_id = f"{duplicate_name}2"

    # Something weird with Colin White

    if player_eh_id == "COLIN.":  # Not covered by tests
        player_eh_id = "COLIN.WHITE2"

    return player_name, player_eh_id


class Player:
    """Class instance for player information and statistics."""

    def __init__(self, player_id: int | str, backend: Literal["polars", "pandas"] = "polars"):
        """Instantiates player information."""
        # Setting up initial information

        self.backend = backend  # Whether to use polars or pandas as backend for dataframes

        self.player_id = player_id

        self._base_api_url = "https://api-web.nhle.com/v1"
        self.base_url = self._base_api_url + f"/player/{player_id}"
        self.landing_url = self.base_url + "/landing"
        self.current_game_log_url = self.base_url + "/game-log/now"

        self.session = ChickenSession()  # Setting up requests sessions object to re-use

        # Getting the landing page information

        self._landing_info = self._scrape_landing()

        # Basic player information from landing page

        stats_keys = ["featuredStats", "careerTotals", "last5Games", "seasonTotals"]  # dictionary keys to leave behind

        self.player_info = {
            k: v for k, v in self._landing_info.items() if k not in stats_keys and k != "currentTeamRoster"
        }

        self.first_name = self.player_info["firstName"]["default"]
        self.last_name = self.player_info["lastName"]["default"]
        self.player_name = f"{self.first_name} {self.last_name}"

        self.is_active = self.player_info["isActive"]
        self.current_team_id = self.player_info["currentTeamId"]
        self.current_team = self.player_info["currentTeamAbbrev"]
        self.current_team_name = self.player_info["teamCommonName"]["default"]
        self.current_team_full_name = self.player_info["fullTeamName"]["default"]
        self.current_team_full_name_fr = self.player_info["fullTeamName"]["fr"]

        # Basic stats from landing page

        self._featured_stats = self._landing_info["featuredStats"]
        self._current_featured_season = self._featured_stats["season"]
        self._featured_regular_season_stats = self._featured_stats["regularSeason"]["subSeason"]
        self._featured_career_stats = self._featured_stats["regularSeason"]["career"]

        self._career_totals = self._landing_info["careerTotals"]
        self._career_regular_season_stats = self._career_totals["regularSeason"]
        self._career_playoff_stats = self._career_totals.get("playoffs")

        self._last_five_games = self._landing_info["last5Games"]

        self._season_totals = self._landing_info["seasonTotals"]

        # Scraping game log information

        self._current_game_logs = self._scrape_current_logs()
        self._game_logs = self._current_game_logs["gameLog"]

        # Basic stats from game logs

        self._active_seasons_data = {x["season"]: x["gameTypes"] for x in self._current_game_logs["playerStatsSeasons"]}

        self.active_seasons = [k for k, v in self._active_seasons_data.items() if 2 in v]
        self.playoff_seasons = [k for k, v in self._active_seasons_data.items() if 3 in v]

    def _scrape_landing(self) -> dict:
        """Scrapes landing page information for player."""
        with self.session as s:
            response = s.get(self.landing_url)

        return response.json()

    def _scrape_current_logs(self) -> dict:
        """Scrapes game logs for latest season for player."""
        with self.session as s:
            response = s.get(self.current_game_log_url)

        return response.json()

    def _munge_career_regular_season_stats(self) -> None:
        """Docstring."""
        old_stats = self._career_regular_season_stats

        new_stats = {
            "season": self._current_featured_season,
            "games_played": old_stats.get("gamesPlayed"),
            "goals": old_stats.get("goals"),
            "shots": old_stats.get("shots"),
            "shooting_pct": old_stats.get("shootingPctg"),
            "ot_goals": old_stats.get("otGoals"),
            "game_winning_goals": old_stats.get("gameWinningGoals"),
            "pp_goals": old_stats.get("powerPlayGoals"),
            "sh_goals": old_stats.get("shorthandedGoals"),
            "assists": old_stats.get("assists"),
            "pp_assists": old_stats.get("powerPlayPoints", 0) - old_stats.get("powerPlayGoals", 0),
            "sh_assists": old_stats.get("shorthandedPoints", 0) - old_stats.get("shorthandedGoals", 0),
            "points": old_stats.get("points"),
            "plus_minus": old_stats.get("plusMinus"),
            "pp_points": old_stats.get("powerPlayPoints"),
            "sh_points": old_stats.get("shorthandedPoints"),
            "pim": old_stats.get("pim"),
        }

        self._career_regular_season_stats = new_stats
