from __future__ import annotations

from functools import cached_property
import re
from typing import TYPE_CHECKING, cast

import polars as pl

if TYPE_CHECKING:
    import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from requests.exceptions import RetryError
from unidecode import unidecode

from chickenstats.chicken_nhl._corrections import html_rosters_fixes
from chickenstats.chicken_nhl._player_names import correct_player_name
from chickenstats.chicken_nhl.team import team_codes
from chickenstats.chicken_nhl.validation_pydantic import HTMLRosterPlayer
from chickenstats.chicken_nhl.validation_polars import html_rosters_polars_schema
from chickenstats.chicken_nhl._docstrings import _GAME_HTML_ROSTERS_DF_DOC, _GAME_HTML_ROSTERS_DOC, shared_doc
from chickenstats.chicken_nhl._game_core import _GameBase


class _GameHTMLRostersMixin(_GameBase):
    def _fetch_html_rosters(self) -> list:
        """Fetch and cache raw HTML roster data on ``self._raw_html_rosters``.

        Idempotent. Active players come from the first two tables, scratches from
        tables 3-4 (if present). Returns an empty list on 404 or RetryError.
        """
        if self._raw_html_rosters is not None:
            return self._raw_html_rosters

        try:
            page = self._requests_session.get(self.html_rosters_endpoint)
            if page.status_code == 404:
                self._raw_html_rosters = []
                return self._raw_html_rosters
            soup = BeautifulSoup(page.content.decode("ISO-8859-1"), "lxml", multi_valued_attributes=None)
        except RetryError:
            self._raw_html_rosters = []
            return self._raw_html_rosters

        td_dict: dict = {"align": "center", "class": ["teamHeading + border", "teamHeading + border "], "width": "50%"}
        teamsoup = soup.find_all("td", cast(dict, td_dict))
        if not teamsoup:
            self._raw_html_rosters = []
            return self._raw_html_rosters

        table_dict = {
            "align": "center",
            "border": "0",
            "cellpadding": "0",
            "cellspacing": "0",
            "width": "100%",
            "xmlns:ext": False,
        }
        team_list = ["AWAY", "HOME"]
        team_names = {}
        raw_player_list = []

        # Extract team names
        for idx, venue in enumerate(team_list):
            team_name = unidecode(teamsoup[idx].get_text().encode("latin-1").decode("utf-8")).upper()
            team_names[venue] = "ARIZONA COYOTES" if team_name == "PHOENIX COYOTES" else team_name

        all_tables = soup.find_all("table", cast(dict, table_dict))
        if len(all_tables) < 2:
            self._raw_html_rosters = []
            return self._raw_html_rosters

        # Extract active players (first two tables)
        for idx, venue in enumerate(team_list):
            team_table = all_tables[idx]

            # Starters are bold ("bold", "bold italic", etc.); player names are every 3rd element
            bold_tds = [
                td.get_text(separator=" ", strip=True)  # type: ignore[call-arg]
                for td in team_table.find_all("td", {"class": re.compile(r"bold", re.IGNORECASE)})
            ]
            starters = [bold_tds[i] for i in range(2, len(bold_tds), 3)]

            all_tds = [td.get_text(separator=" ", strip=True) for td in team_table.find_all("td")]  # type: ignore[call-arg]
            if not all_tds:
                continue

            active_array = np.array(all_tds).reshape(-1, 3)

            # Skip the header row
            for row in active_array[1:]:
                headers = ["jersey", "position", "player_name"] if len(row) == 3 else ["jersey", "player_name"]
                p_dict = dict(zip(headers, row, strict=True))

                p_dict.update(
                    {
                        "team_name": team_names[venue],
                        "team_venue": venue,
                        "status": "ACTIVE",
                        "starter": 1 if p_dict.get("player_name") in starters else 0,
                    }
                )
                raw_player_list.append(p_dict)

        # Extract scratches (tables 3 and 4, if present)
        if len(all_tables) > 2:
            for idx, venue in enumerate(team_list):
                if len(all_tables) > idx + 2:
                    scratch_tds = [td.get_text(separator=" ", strip=True) for td in all_tables[idx + 2].find_all("td")]  # type: ignore[call-arg]
                    if len(scratch_tds) > 1:
                        scratch_array = np.array(scratch_tds).reshape(-1, 3)[1:]
                        for row in scratch_array:
                            headers = (
                                ["jersey", "position", "player_name"] if len(row) == 3 else ["jersey", "player_name"]
                            )
                            p_dict = dict(zip(headers, row, strict=True))
                            p_dict.update(
                                {"team_name": team_names[venue], "team_venue": venue, "status": "SCRATCH", "starter": 0}
                            )
                            raw_player_list.append(p_dict)

        del soup
        self._raw_html_rosters = raw_player_list
        return self._raw_html_rosters

    def _munge_single_html_player(self, raw_player: dict) -> dict:
        """Worker to clean, fix, and validate a single HTML roster record."""
        raw_name = raw_player.get("player_name", "").upper()

        # Remove Captain/Alternate (C)/(A) indicators
        clean_name = re.sub(r"\(\s?(.*)\)", "", raw_name)
        clean_name = clean_name.strip().encode("latin-1").decode("utf-8")
        raw_player["player_name"] = unidecode(clean_name)
        raw_player["position"] = raw_player.get("position")

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
        if not raw_players:
            return []

        cleaned_players = [self._munge_single_html_player(player) for player in raw_players]

        return sorted(cleaned_players, key=lambda k: (k["team_venue"], k["status"], k["player_name"]))

    @property
    @shared_doc(_GAME_HTML_ROSTERS_DF_DOC)
    def html_rosters_df(self) -> pd.DataFrame | pl.DataFrame:
        """html_rosters_df — docstring lives in _docstrings._GAME_HTML_ROSTERS_DF_DOC."""
        return self._finalize_dataframe(data=self.html_rosters, schema=html_rosters_polars_schema)
