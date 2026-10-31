from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from functools import cached_property
import logging
import re
from typing import TYPE_CHECKING, cast

import numpy as np
import polars as pl

if TYPE_CHECKING:
    import pandas as pd
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
from unidecode import unidecode

from chickenstats.chicken_nhl._corrections import html_shifts_fixes, individual_shifts_fixes
from chickenstats.chicken_nhl._game_utils import clock, decode_report, is_cut_off, period_length
from chickenstats.chicken_nhl._player_names import correct_player_name, correct_names_dict
from chickenstats.chicken_nhl.team import team_codes
from chickenstats.chicken_nhl.validation_pydantic import PlayerShift
from chickenstats.chicken_nhl.validation_polars import shifts_polars_schema
from chickenstats.chicken_nhl._docstrings import _GAME_SHIFTS_DF_DOC, _GAME_SHIFTS_DOC, shared_doc
from chickenstats.chicken_nhl._game_core import _GameBase

logger = logging.getLogger(__name__)


class _GameHTMLShiftsMixin(_GameBase):
    def _parse_team_shifts(self, team_venue: str, response) -> list:
        """Parse shift data for a single team (HOME or AWAY) from an already-fetched response."""
        team_shifts = []

        soup = BeautifulSoup(decode_report(response.content), "lxml", multi_valued_attributes=None)

        team_name_td = soup.find("td", {"align": "center", "class": "teamHeading + border"})
        if not team_name_td:
            return team_shifts

        team_name = unidecode(team_name_td.get_text())
        if team_name == "PHOENIX COYOTES":
            team_name = "ARIZONA COYOTES"
        elif "CANADIENS" in team_name:
            team_name = "MONTREAL CANADIENS"

        players = soup.find_all("td", {"class": ["playerHeading + border", "lborder + bborder"]})
        # Keyed by jersey, since two teammates can share a name
        players_dict = {}
        full_name = " "
        jersey = None

        for player in players:
            data = player.get_text()
            if ", " in data:
                name = data.split(",", 1)
                last_name = name[0].split(" ", 1)[1].strip()
                first_name = re.sub(r"\(\s?(.+)\)", "", name[1]).strip()
                full_name = f"{first_name} {last_name}"

                if full_name == " ":
                    continue

                jersey = int(name[0].split(" ")[0].strip())
                full_name, eh_id = correct_player_name(player_name=full_name, season=self.season, player_jersey=jersey)
                players_dict[jersey] = {"player_name": full_name, "eh_id": eh_id, "jersey": jersey, "shifts": []}
            else:
                if jersey is not None and full_name != " ":
                    cast(list, players_dict[jersey]["shifts"]).extend([data])

        for player, shifts in players_dict.items():
            # A report written while the game is played can end in the middle of a row; only whole rows are read
            cells = cast(list, shifts["shifts"])
            length = len(cells) // 5
            player_name = cast(str, shifts["player_name"])
            eh_id = shifts["eh_id"]
            team = team_codes.get(team_name, "")
            team_venue_name = team_venue.upper()
            team_jersey = f"{team}{shifts['jersey']}"
            jersey = cast(int, shifts["jersey"])

            for _number, shift in enumerate(np.array(cells[: length * 5]).reshape(length, 5)):
                headers = ["shift_count", "period", "shift_start", "shift_end", "duration"]
                shift_dict = dict(zip(headers, shift.flatten(), strict=True))
                # A shift still being played can have no period or start in the report yet
                if not str(shift_dict["period"]).strip() or not str(shift_dict["shift_start"]).strip():
                    continue
                shift_dict = individual_shifts_fixes(
                    game_id=self.game_id, player_name=player_name, shift_dict=shift_dict
                )

                shift_dict.update(
                    {
                        "season": self.season,
                        "session": self.session,
                        "game_id": self.game_id,
                        "team_name": team_name,
                        "team": team,
                        "team_venue": team_venue_name,
                        "player_name": player_name,
                        "eh_id": eh_id,
                        "team_jersey": team_jersey,
                        "jersey": jersey,
                        "period": int(shift_dict["period"].replace("OT", "4").replace("SO", "5")),
                        "shift_count": int(shift_dict["shift_count"]),
                        "shift_start": unidecode(shift_dict["shift_start"]).strip(),
                        "start_time": unidecode(shift_dict["shift_start"]).strip().split("/", 1)[0].strip(),
                        "shift_end": unidecode(shift_dict["shift_end"]).strip(),
                        "end_time": unidecode(shift_dict["shift_end"]).strip().split("/", 1)[0].strip(),
                    }
                )

                if shift_dict["start_time"] != "31:23":
                    team_shifts.append(shift_dict)

        return team_shifts

    def _fetch_shifts(self) -> list:
        """Fetch shift data for HOME and AWAY teams, concurrently; parse sequentially."""
        if self._raw_shifts is not None:
            return self._raw_shifts

        endpoints = {"HOME": self.home_shifts_endpoint, "AWAY": self.away_shifts_endpoint}

        reports = {"HOME": "TH", "AWAY": "TV"}
        responses: dict = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(self._requests_session.get, url): venue for venue, url in endpoints.items()}
            for future in as_completed(futures):
                venue = futures[future]
                try:
                    response = future.result()
                except RequestException as exc:
                    self._report_failures[reports[venue]] = f"request failed: {type(exc).__name__}"
                    continue
                if response.status_code != 200:
                    self._report_failures[reports[venue]] = f"HTTP {response.status_code}"
                    continue
                if is_cut_off(response.content):
                    self._report_failures[reports[venue]] = "cut off before its end"
                responses[venue] = response

        game_list = []
        for venue, response in responses.items():
            try:
                team_shifts = self._parse_team_shifts(venue, response)
            except Exception as exc:  # noqa: BLE001  # pyright: ignore[reportBroadExceptionCaught]
                logger.debug("Failed to parse shifts for %s venue", venue, exc_info=True)
                self._report_failures[reports[venue]] = f"could not be read: {type(exc).__name__}"
                continue
            if not team_shifts:
                self._report_failures[reports[venue]] = "no shifts in the report"
            game_list.extend(team_shifts)

        self._raw_shifts = game_list
        return self._raw_shifts

    def _munge_shifts(self, raw_shifts: list, actives: dict, scratches: dict) -> list:
        """Transform raw shift data into structured shift dicts."""
        raw_shifts = html_shifts_fixes(self.game_id, self.season, self.session, raw_shifts, actives, scratches)

        period_shifts = {}
        period_max_seconds = {}
        team_goalies = {"HOME": {}, "AWAY": {}}

        # Pass 1: map metadata, clean names, parse times, group by period
        for shift in raw_shifts:
            team_jersey = shift.get("team_jersey", "")
            player_info = actives.get(team_jersey) or scratches.get(team_jersey, {})

            shift["eh_id"] = player_info.get("eh_id", shift.get("eh_id"))
            shift["api_id"] = player_info.get("api_id")
            shift["position"] = player_info.get("position")
            shift["goalie"] = 1 if shift["position"] == "G" else 0
            shift["is_home"] = 1 if shift.get("team_venue") == "HOME" else 0
            shift["is_away"] = 1 if shift.get("team_venue") == "AWAY" else 0

            # Use the roster's name so a player has one name across rosters, shifts and play-by-play
            player_name = player_info.get("player_name")
            if not player_name:
                player_name = (
                    shift.get("player_name", "")
                    .replace("ALEXANDRE", "ALEX")
                    .replace("ALEXANDER", "ALEX")
                    .replace("CHRISTOPHER", "CHRIS")
                )
                player_name = correct_names_dict.get(player_name, player_name)
            shift["player_name"] = player_name

            # Skip malformed time strings instead of raising
            for col in ["start_time", "end_time", "duration"]:
                t_str = shift.get(col, "")
                if ":" not in t_str:
                    continue
                ts = t_str.split(":", 1)
                try:
                    shift[f"{col}_seconds"] = 60 * int(ts[0]) + int(ts[1])
                except ValueError:
                    continue

            # Base Clock Fixes
            if not shift.get("end_time") or shift["end_time"].strip() == "":
                shift["end_time_seconds"] = shift.get("start_time_seconds", 0) + shift.get("duration_seconds", 0)
                shift["end_time"] = str(timedelta(seconds=shift.get("end_time_seconds"))).split(":", 1)[1]

            if shift["shift_end"] == "0:00 / 0:00":
                fixed_end_time_seconds = period_length(shift["period"], self._overtime)
                fixed_end_time = clock(fixed_end_time_seconds)
                fixed_shift_end = f"{fixed_end_time} / 0:00"

                fixed_duration_seconds = fixed_end_time_seconds - shift.get("start_time_seconds", 0)

                shift.update(
                    {
                        "end_time": fixed_end_time,
                        "end_time_seconds": fixed_end_time_seconds,
                        "shift_end": fixed_shift_end,
                        "duration_seconds": fixed_duration_seconds,
                    }
                )
                shift["duration"] = str(timedelta(seconds=shift["duration_seconds"])).split(":", 1)[1]

            p = shift.get("period", 1)
            if p not in period_shifts:
                period_shifts[p] = []
                period_max_seconds[p] = 0
                team_goalies["HOME"][p] = []
                team_goalies["AWAY"][p] = []

            period_shifts[p].append(shift)

            end_sec = shift.get("end_time_seconds", 0)
            if end_sec > period_max_seconds[p]:
                period_max_seconds[p] = end_sec

            if shift["goalie"] == 1:
                team_goalies[shift["team_venue"]][p].append(shift)

        if not period_shifts:
            return []

        final_shifts = []

        # Pass 2: apply period-dependent fixes
        for period, shifts in sorted(period_shifts.items()):
            max_seconds = period_max_seconds[period]
            expected_total_seconds = period_length(period, self._overtime)

            # Fix broken clocks and missing goalie shift ends
            for shift in shifts:
                start_seconds = shift.get("start_time_seconds", 0)
                end_seconds = shift.get("end_time_seconds", 0)

                needs_clock_fix = start_seconds > end_seconds
                needs_goalie_fix = shift["goalie"] == 1 and (
                    not shift.get("shift_end") or shift["shift_end"] == "0:00 / 0:00"
                )

                if needs_clock_fix or needs_goalie_fix:
                    if max_seconds < expected_total_seconds:
                        # Period ended early, cap shift at max_sec
                        end_time = f"{max_seconds // 60}:{max_seconds % 60:02d}"
                        remaining_seconds = expected_total_seconds - max_seconds
                        remaining_time = f"{remaining_seconds // 60}:{remaining_seconds % 60:02d}"
                        shift.update(
                            {
                                "end_time_seconds": max_seconds,
                                "end_time": end_time,
                                "shift_end": f"{end_time} / {remaining_time}",
                            }
                        )
                    else:
                        # Period went the full length
                        end_time = clock(expected_total_seconds)
                        shift.update(
                            {
                                "end_time_seconds": expected_total_seconds,
                                "end_time": end_time,
                                "shift_end": f"{end_time} / 0:00",
                            }
                        )

                    shift["duration_seconds"] = shift["end_time_seconds"] - start_seconds
                    shift["duration"] = f"{shift['duration_seconds'] // 60}:{shift['duration_seconds'] % 60:02d}"

                final_shifts.append(PlayerShift.model_validate(shift).model_dump())

            # Inject missing goalies
            for team in ["HOME", "AWAY"]:
                if len(team_goalies[team][period]) < 1:
                    base_goalie = None

                    if period == 1:
                        base_goalie = next(
                            (
                                x
                                for x in actives.values()
                                if x.get("position") == "G" and x.get("team_venue") == team and x.get("starter") == 1
                            ),
                            None,
                        )
                        if not base_goalie:
                            for p_idx in sorted(period_shifts.keys()):
                                if team_goalies[team].get(p_idx):
                                    base_goalie = team_goalies[team][p_idx][0]
                                    break
                    else:
                        prev_goalies = team_goalies[team].get(period - 1)
                        if prev_goalies:
                            base_goalie = prev_goalies[-1]

                    if base_goalie:
                        g_shift = dict(base_goalie)
                        g_shift.update(
                            {
                                "season": self.season,
                                "session": self.session,
                                "game_id": self.game_id,
                                "period": period,
                                "team_venue": team,
                                "goalie": 1,
                                "shift_count": 1,
                                "is_home": 1 if team == "HOME" else 0,
                                "is_away": 1 if team == "AWAY" else 0,
                                "number": 0,
                                "start_time": "0:00",
                                "start_time_seconds": 0,
                            }
                        )

                        g_shift["shift_start"] = f"0:00 / {clock(expected_total_seconds)}"

                        if max_seconds < expected_total_seconds:
                            end_time = f"{max_seconds // 60}:{max_seconds % 60:02d}"
                            remaining_seconds = expected_total_seconds - max_seconds
                            remaining_time = f"{remaining_seconds // 60}:{remaining_seconds % 60:02d}"

                            g_shift.update(
                                {
                                    "end_time_seconds": max_seconds,
                                    "end_time": end_time,
                                    "duration_seconds": max_seconds,
                                    "duration": end_time,
                                    "shift_end": f"{end_time} / {remaining_time}",
                                }
                            )
                        else:
                            end_time = clock(expected_total_seconds)

                            g_shift.update(
                                {
                                    "end_time_seconds": expected_total_seconds,
                                    "end_time": end_time,
                                    "duration_seconds": expected_total_seconds,
                                    "duration": end_time,
                                    "shift_end": f"{end_time} / 0:00",
                                }
                            )

                        final_shifts.append(PlayerShift.model_validate(g_shift).model_dump())

        return final_shifts

    @cached_property
    @shared_doc(_GAME_SHIFTS_DOC)
    def shifts(self) -> list:
        """Shifts — docstring lives in _docstrings._GAME_SHIFTS_DOC."""
        self._prefetch_reports(
            (self._fetch_html_rosters, ("html_rosters", "rosters")), (self._fetch_shifts, ("shifts", "changes"))
        )
        raw_shifts = self._fetch_shifts()
        self._check_reports("TH", "TV")
        if not raw_shifts:
            return []

        actives = {
            player["team_jersey"]: player
            for player in self.rosters
            if player.get("team_jersey") and player.get("status") == "ACTIVE"
        }

        scratches = {
            player["team_jersey"]: player
            for player in self.rosters
            if player.get("team_jersey") and player.get("status") == "SCRATCH"
        }

        final_shifts = self._munge_shifts(raw_shifts, actives, scratches)

        return sorted(final_shifts, key=lambda k: (k["period"], k["start_time_seconds"], k["team_venue"]))

    @property
    @shared_doc(_GAME_SHIFTS_DF_DOC)
    def shifts_df(self) -> pd.DataFrame | pl.DataFrame:
        """shifts_df — docstring lives in _docstrings._GAME_SHIFTS_DF_DOC."""
        return self._finalize_dataframe(data=self.shifts, schema=shifts_polars_schema)
