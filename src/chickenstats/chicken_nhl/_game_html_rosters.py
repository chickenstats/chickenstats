from __future__ import annotations

from functools import cached_property
import re


import numpy as np
from unidecode import unidecode

from chickenstats.chicken_nhl._corrections import html_rosters_fixes
from chickenstats.chicken_nhl._player_names import correct_player_name
from chickenstats.chicken_nhl.team import team_codes
from chickenstats.chicken_nhl.validation_pydantic import HTMLRosterPlayer
from chickenstats.chicken_nhl.validation_polars import html_rosters_polars_schema
from chickenstats.utilities.types import FrameT
from chickenstats.chicken_nhl._docstrings import _GAME_HTML_ROSTERS_DF_DOC, _GAME_HTML_ROSTERS_DOC, shared_doc
from chickenstats.chicken_nhl._game_core import FIRST_API_COORDS_SEASON, _GameBase
from chickenstats.chicken_nhl._game_utils import node_text, node_words, parse_report


def _roster_table_players(cells: list, team_name: str, venue: str, status: str, starters: list) -> list[dict]:
    """Read a roster table's cells, three to a row after the header row, as one dict per player."""
    players = []
    for row in np.array(cells).reshape(-1, 3)[1:]:
        player = dict(zip(["jersey", "position", "player_name"], row, strict=True))
        player.update(
            {
                "team_name": team_name,
                "team_venue": venue,
                "status": status,
                "starter": 1 if player["player_name"] in starters else 0,
            }
        )
        players.append(player)

    return players


class _GameHTMLRostersMixin(_GameBase[FrameT]):
    def _fetch_html_rosters(self) -> list:
        """Fetch and cache raw HTML roster data on ``self._raw_html_rosters``.

        Idempotent. Active players come from the first two tables, scratches from
        tables 3-4 (if present). Returns an empty list, and records an RO failure, when the
        report cannot be read or has no rosters.
        """
        if self._raw_html_rosters is not None:
            return self._raw_html_rosters

        page = self._get_report(self.html_rosters_endpoint, "RO")
        if page is None:
            self._raw_html_rosters = []
            return self._raw_html_rosters

        root = parse_report(page.content)
        team_cells = (
            []
            if root is None
            else root.xpath(
                "//td[@align='center' and @width='50%' and "
                "(@class='teamHeading + border' or @class='teamHeading + border ')]"
            )
        )
        if not team_cells:
            self._report_failures["RO"] = "no rosters in the report"
            self._raw_html_rosters = []
            return self._raw_html_rosters

        team_list = ["AWAY", "HOME"]
        team_names = {}
        raw_player_list = []

        # Extract team names
        for idx, venue in enumerate(team_list):
            team_name = unidecode(node_text(team_cells[idx])).upper()
            if team_name == "PHOENIX COYOTES":
                team_name = "ARIZONA COYOTES"
            # Some older reports write it as CANADIENS MONTREAL
            elif "CANADIENS" in team_name:
                team_name = "MONTREAL CANADIENS"
            team_names[venue] = team_name

        # The roster tables are the plain ones: the page's layout tables declare xmlns:ext
        all_tables = root.xpath(
            "//table[@align='center' and @border='0' and @cellpadding='0' and @cellspacing='0' "
            "and @width='100%' and not(@*[name()='xmlns:ext'])]"
        )
        if len(all_tables) < 2:
            self._report_failures["RO"] = "no rosters in the report"
            self._raw_html_rosters = []
            return self._raw_html_rosters

        # Extract active players (first two tables)
        for venue, table in zip(team_list, all_tables[:2], strict=True):
            # Starters are bold ("bold", "bold italic", etc.); player names are every 3rd element
            bold_tds = [
                node_words(td) for td in table.xpath(".//td[contains(translate(@class, 'BOLD', 'bold'), 'bold')]")
            ]
            starters = [bold_tds[i] for i in range(2, len(bold_tds), 3)]

            all_tds = [node_words(td) for td in table.xpath(".//td")]
            raw_player_list.extend(_roster_table_players(all_tds, team_names[venue], venue, "ACTIVE", starters))

        # Extract scratches (tables 3 and 4, if present)
        for venue, table in zip(team_list, all_tables[2:], strict=False):
            scratch_tds = [node_words(td) for td in table.xpath(".//td")]
            if len(scratch_tds) > 1:
                raw_player_list.extend(_roster_table_players(scratch_tds, team_names[venue], venue, "SCRATCH", []))

        self._raw_html_rosters = raw_player_list
        return self._raw_html_rosters

    def _munge_single_html_player(self, raw_player: dict) -> dict:
        """Worker to clean, fix, and validate a single HTML roster record."""
        raw_name = raw_player.get("player_name", "").upper()

        # Remove Captain/Alternate (C)/(A) indicators
        clean_name = re.sub(r"\(\s?(.*)\)", "", raw_name)
        # Older reports can also give a formal name, as in COLIN (JOHN) WHITE  (A)
        if self.season < FIRST_API_COORDS_SEASON:
            clean_name = " ".join(re.sub(r"\(.*?\)", "", raw_name).split())
        clean_name = clean_name.strip()
        raw_player["player_name"] = unidecode(clean_name)

        player = html_rosters_fixes(self.game_id, raw_player)

        player["jersey"] = int(player["jersey"])
        player["team"] = team_codes.get(player["team_name"])
        player["team_jersey"] = f"{player['team']}{player['jersey']}"

        player["player_name"], player["eh_id"] = correct_player_name(
            player_name=player["player_name"],
            season=self.season,
            player_position=player["position"],
            player_jersey=player["team_jersey"],
        )

        player.update({"season": int(self.season), "session": self.session, "game_id": self.game_id})

        return HTMLRosterPlayer.model_validate(player).model_dump()

    @cached_property
    @shared_doc(_GAME_HTML_ROSTERS_DOC)
    def html_rosters(self) -> list:
        """html_rosters — docstring lives in _docstrings._GAME_HTML_ROSTERS_DOC."""
        raw_players = self._fetch_html_rosters()
        self._raise_for_reports("RO")
        if not raw_players:
            return []

        cleaned_players = [self._munge_single_html_player(player) for player in raw_players]

        return sorted(cleaned_players, key=lambda k: (k["team_venue"], k["status"], k["player_name"]))

    @property
    @shared_doc(_GAME_HTML_ROSTERS_DF_DOC)
    def html_rosters_df(self) -> FrameT:
        """html_rosters_df — docstring lives in _docstrings._GAME_HTML_ROSTERS_DF_DOC."""
        return self._finalize_dataframe(data=self.html_rosters, schema=html_rosters_polars_schema)
