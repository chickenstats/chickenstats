from __future__ import annotations

from functools import cached_property

import numpy as np
import pandas as pd
import polars as pl
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

from chickenstats.chicken_nhl._game_utils import (
    _EXT_SOURCE_KEYS,
    _EXT_TARGET_KEYS,
    aggregate_players,
    calculate_score_adjustment,
    prefetch_concurrent,
)
from chickenstats.chicken_nhl.validation_pydantic import PBPEvent, PBPEventExt, XGFields
from chickenstats.chicken_nhl.validation_polars import pbp_polars_schema
from chickenstats.chicken_nhl._game_core import _GameBase

model_version = "0.1.1"


class _GamePBPMixin(_GameBase):
    def _merge_pbp_events(self, html_events: list, api_events: list, changes: list, rosters: list) -> list:
        """O(N) Worker to merge HTML events, API events, and Line Changes with exact parity."""
        rosters_lookup = {player["eh_id"]: player for player in rosters if player["status"] == "ACTIVE"}

        api_index = {}
        for api_ev in api_events:
            key = (api_ev["period"], api_ev["period_seconds"], api_ev["event"])
            if key not in api_index:
                api_index[key] = []
            api_index[key].append(api_ev)

        game_list = []
        non_team_events = [
            "STOP",
            "ANTHEM",
            "PGSTR",
            "PGEND",
            "PSTR",
            "PEND",
            "EISTR",
            "EIEND",
            "GEND",
            "SOC",
            "EGT",
            "PBOX",
            "PRDY",
            "POFF",
            "GOFF",
        ]

        for event in html_events:
            if event["event"] == "EGPID":
                continue

            event_data = dict(event)
            key = (event["period"], event["period_seconds"], event["event"])
            candidates = api_index.get(key, [])
            api_matches = []

            for x in candidates:
                if x["version"] != event.get("version", 1):
                    continue

                if event["event"] in non_team_events:
                    api_matches.append(x)
                elif event["event"] == "CHL" and event.get("event_team") is None:
                    api_matches.append(x)
                elif event["event"] == "CHL" and event.get("event_team") is not None:
                    if x.get("event_team") == event["event_team"]:
                        api_matches.append(x)
                elif event["event"] == "PENL":
                    if (
                        x.get("event_team") == event.get("event_team")
                        and x.get("player_1_eh_id") == event.get("player_1_eh_id")
                        and x.get("player_2_eh_id") == event.get("player_2_eh_id")
                        and x.get("player_3_eh_id") == event.get("player_3_eh_id")
                    ):
                        api_matches.append(x)
                elif event["event"] == "BLOCK" and event.get("player_1") == "TEAMMATE":
                    if x.get("event_team") == event.get("event_team"):
                        api_matches.append(x)
                else:
                    if x.get("event_team") == event.get("event_team") and x.get("player_1_eh_id") == event.get(
                        "player_1_eh_id"
                    ):
                        api_matches.append(x)

            if event["event"] == "FAC" and len(api_matches) == 0:
                api_matches = [x for x in candidates if x["version"] == event.get("version", 1)]

            if len(api_matches) == 1:
                api_match = api_matches[0]
                event_data.update(
                    {
                        "event_idx_api": api_match.get("event_idx"),
                        "coords_x": api_match.get("coords_x"),
                        "coords_y": api_match.get("coords_y"),
                        "player_1_eh_id_api": api_match.get("player_1_eh_id"),
                        "player_1_api_id": api_match.get("player_1_api_id"),
                        "player_1_type": api_match.get("player_1_type"),
                        "player_2_eh_id_api": api_match.get("player_2_eh_id"),
                        "player_2_api_id": api_match.get("player_2_api_id"),
                        "player_2_type": api_match.get("player_2_type"),
                        "player_3_eh_id_api": api_match.get("player_3_eh_id"),
                        "player_3_api_id": api_match.get("player_3_api_id"),
                        "player_3_type": api_match.get("player_3_type"),
                        "version_api": api_match.get("version", 1),
                    }
                )
                if event["event"] == "BLOCK" and event.get("player_1") == "TEAMMATE":
                    event_data.update(
                        {
                            "player_1": api_match.get("player_1", event["player_1"]),
                            "player_1_eh_id": api_match.get("player_1_eh_id", event.get("player_1_eh_id")),
                            "player_1_position": api_match.get("player_1_position", event.get("player_1_position")),
                        }
                    )

            if event["event"] not in non_team_events and event.get("player_1") not in ["BENCH", "REFEREE"]:
                for player_lookup in ["player_1", "player_2", "player_3"]:
                    if event_data.get(player_lookup) and not event_data.get(f"{player_lookup}_api_id"):
                        event_data[f"{player_lookup}_api_id"] = rosters_lookup.get(
                            event[f"{player_lookup}_eh_id"], {}
                        ).get("api_id")

            game_list.append(event_data)

        game_list.extend(changes)
        sort_dict = {
            "PGSTR": 1,
            "PGEND": 2,
            "ANTHEM": 3,
            "EGT": 3,
            "CHL": 3,
            "DELPEN": 3,
            "BLOCK": 3,
            "GIVE": 3,
            "HIT": 3,
            "MISS": 3,
            "SHOT": 3,
            "TAKE": 3,
            "GOAL": 5,
            "STOP": 6,
            "PENL": 7,
            "PBOX": 7,
            "PSTR": 7,
            "CHANGE": 8,
            "EISTR": 9,
            "EIEND": 10,
            "FAC": 12,
            "PEND": 13,
            "SOC": 14,
            "GEND": 15,
            "GOFF": 16,
        }

        for event in game_list:
            event.update(
                {
                    "game_date": self.game_date,
                    "home_team": self.home_team["abbrev"],
                    "away_team": self.away_team["abbrev"],
                    "version": event.get("version", 1),
                }
            )
            event["sort_value"] = (
                event.get("event_idx")
                if (event["period"] == 5 and self.session == "R")
                else sort_dict.get(event["event"], 99)
            )

        return sorted(game_list, key=lambda k: (k["period"], k["period_seconds"], k.get("sort_value", 99)))

    def _track_pbp_state(self, merged_events: list, actives: dict) -> list:
        home_score, away_score = 0, 0
        home_on_ice, away_on_ice = {}, {}
        prev_event_type, prev_event_team = None, None
        _last_fac_sec, _last_fac_x, _last_fac_y, _last_fac_zone, _last_fac_team = None, None, None, None, None

        hd1 = Polygon(np.array([[69, -9], [89, -9], [89, 9], [69, 9]]))
        hd2 = Polygon(np.array([[-69, -9], [-89, -9], [-89, 9], [-69, 9]]))
        d1 = Polygon(
            np.array(
                [[89, 9], [89, -9], [69, -22], [54, -22], [54, -9], [44, -9], [44, 9], [54, 9], [54, 22], [69, 22]]
            )
        )
        d2 = Polygon(
            np.array(
                [
                    [-89, 9],
                    [-89, -9],
                    [-69, -22],
                    [-54, -22],
                    [-54, -9],
                    [-44, -9],
                    [-44, 9],
                    [-54, 9],
                    [-54, 22],
                    [-69, 22],
                ]
            )
        )

        # CACHE INITIALIZATION
        h_ice = aggregate_players([])
        a_ice = aggregate_players([])
        ice_changed = True

        # Mapping faceoff events to game seconds
        faceoff_events = {
            (event["period"], event["game_seconds"]): {
                "coords_x": event.get("coords_x"),
                "coords_y": event.get("coords_y"),
                "zone": event.get("zone"),
                "event_team": event.get("event_team"),
            }
            for event in merged_events
            if event["event"] == "FAC"
            # and event["game_seconds"] not in [0, 1200, 2400, 3600, 4800, 6000, 7200, 8400]
        }

        for idx, event in enumerate(merged_events):
            if prev_event_type == "GOAL":
                if prev_event_team == event["home_team"]:
                    home_score += 1
                elif prev_event_team == event["away_team"]:
                    away_score += 1

            event.update(
                {
                    "home_score": home_score,
                    "away_score": away_score,
                    "home_score_diff": home_score - away_score,
                    "away_score_diff": away_score - home_score,
                    "score_state": f"{home_score}v{away_score}",
                    "score_diff": home_score - away_score,
                }
            )

            if event.get("event_team") == event["home_team"]:
                event.update({"opp_team": event["away_team"], "is_home": 1, "is_away": 0})
            elif event.get("event_team") == event["away_team"]:
                event.update({"opp_team": event["home_team"], "is_home": 0, "is_away": 1})
            else:
                event.update(
                    {"event_team": event["home_team"], "opp_team": event["away_team"], "is_home": 0, "is_away": 0}
                )

            # ICE CACHING LOGIC: Only re-aggregate if a change happens
            if event["event"] == "CHANGE":
                on_jerseys = set(str(event["change_on_jersey"]).split(", ")) if event.get("change_on_jersey") else set()
                off_jerseys = (
                    set(str(event["change_off_jersey"]).split(", ")) if event.get("change_off_jersey") else set()
                )
                duplicate_jerseys = on_jerseys & off_jerseys

                for tj in on_jerseys - duplicate_jerseys:
                    if tj in actives:
                        if event["team_venue"] == "HOME":
                            home_on_ice[tj] = actives[tj]
                        else:
                            away_on_ice[tj] = actives[tj]
                for tj in off_jerseys - duplicate_jerseys:
                    if event["team_venue"] == "HOME":
                        home_on_ice.pop(tj, None)
                    else:
                        away_on_ice.pop(tj, None)
                ice_changed = True

            if ice_changed:
                h_ice = aggregate_players(list(home_on_ice.values()))
                a_ice = aggregate_players(list(away_on_ice.values()))
                ice_changed = False

            event.update(
                {
                    "home_skaters": h_ice["ALL"]["count"] - h_ice["G"]["count"],
                    "away_skaters": a_ice["ALL"]["count"] - a_ice["G"]["count"],
                    "home_on_eh_id": h_ice["ALL"]["eh_ids"],
                    "home_on_api_id": h_ice["ALL"]["api_ids"],
                    "home_on": h_ice["ALL"]["names"],
                    "home_on_positions": h_ice["ALL"]["positions"],
                    "home_forwards_eh_id": h_ice["F"]["eh_ids"],
                    "home_forwards_api_id": h_ice["F"]["api_ids"],
                    "home_forwards": h_ice["F"]["names"],
                    "home_forwards_positions": h_ice["F"]["positions"],
                    "home_forwards_count": h_ice["F"]["count"],
                    "home_defense_eh_id": h_ice["D"]["eh_ids"],
                    "home_defense_api_id": h_ice["D"]["api_ids"],
                    "home_defense": h_ice["D"]["names"],
                    "home_defense_positions": h_ice["D"]["positions"],
                    "home_defense_count": h_ice["D"]["count"],
                    "home_goalie_eh_id": h_ice["G"]["eh_ids"],
                    "home_goalie_api_id": h_ice["G"]["api_ids"],
                    "home_goalie": h_ice["G"]["names"],
                    "away_on_eh_id": a_ice["ALL"]["eh_ids"],
                    "away_on_api_id": a_ice["ALL"]["api_ids"],
                    "away_on": a_ice["ALL"]["names"],
                    "away_on_positions": a_ice["ALL"]["positions"],
                    "away_forwards_eh_id": a_ice["F"]["eh_ids"],
                    "away_forwards_api_id": a_ice["F"]["api_ids"],
                    "away_forwards": a_ice["F"]["names"],
                    "away_forwards_positions": a_ice["F"]["positions"],
                    "away_forwards_count": a_ice["F"]["count"],
                    "away_defense_eh_id": a_ice["D"]["eh_ids"],
                    "away_defense_api_id": a_ice["D"]["api_ids"],
                    "away_defense": a_ice["D"]["names"],
                    "away_defense_positions": a_ice["D"]["positions"],
                    "away_defense_count": a_ice["D"]["count"],
                    "away_goalie_eh_id": a_ice["G"]["eh_ids"],
                    "away_goalie_api_id": a_ice["G"]["api_ids"],
                    "away_goalie": a_ice["G"]["names"],
                }
            )

            event["home_forwards_percent"] = event["home_forwards_count"] / max(1, event["home_skaters"])
            event["away_forwards_percent"] = event["away_forwards_count"] / max(1, event["away_skaters"])

            h_str = "E" if not event["home_goalie"] else event["home_skaters"]
            a_str = "E" if not event["away_goalie"] else event["away_skaters"]

            is_h_ev = event["event_team"] == event["home_team"]

            event["strength_state"] = f"{a_str}v{h_str}" if not is_h_ev else f"{h_str}v{a_str}"
            if "PENALTY SHOT" in str(event.get("description", "")):
                event["strength_state"] = "1v0"
            if event["period"] == 5 and self.session == "R":
                event["strength_state"] = "1v0"
            if (event["home_skaters"] > 5 and event["home_goalie"]) or (
                event["away_skaters"] > 5 and event["away_goalie"]
            ):
                event["strength_state"] = "ILLEGAL"

            tm_pre, opp_pre = ("home", "away") if is_h_ev else ("away", "home")

            event.update(
                {
                    "event_team_skaters": event[f"{tm_pre}_skaters"],
                    "teammates_eh_id": event[f"{tm_pre}_on_eh_id"],
                    "teammates_api_id": event[f"{tm_pre}_on_api_id"],
                    "teammates": event[f"{tm_pre}_on"],
                    "teammates_positions": event[f"{tm_pre}_on_positions"],
                    "forwards_eh_id": event[f"{tm_pre}_forwards_eh_id"],
                    "forwards_api_id": event[f"{tm_pre}_forwards_api_id"],
                    "forwards": event[f"{tm_pre}_forwards"],
                    "forwards_count": event[f"{tm_pre}_forwards_count"],
                    "forwards_percent": event[f"{tm_pre}_forwards_percent"],
                    "defense_eh_id": event[f"{tm_pre}_defense_eh_id"],
                    "defense_api_id": event[f"{tm_pre}_defense_api_id"],
                    "defense": event[f"{tm_pre}_defense"],
                    "defense_count": event[f"{tm_pre}_defense_count"],
                    "own_goalie_eh_id": event[f"{tm_pre}_goalie_eh_id"],
                    "own_goalie_api_id": event[f"{tm_pre}_goalie_api_id"],
                    "own_goalie": event[f"{tm_pre}_goalie"],
                    "opp_strength_state": f"{a_str}v{h_str}" if is_h_ev else f"{h_str}v{a_str}",
                    "opp_score_state": f"{event['away_score']}v{event['home_score']}"
                    if is_h_ev
                    else f"{event['home_score']}v{event['away_score']}",
                    "opp_score_diff": event["away_score_diff"] if is_h_ev else event["home_score_diff"],
                    "opp_team_skaters": event[f"{opp_pre}_skaters"],
                    "opp_team_on_eh_id": event[f"{opp_pre}_on_eh_id"],
                    "opp_team_on_api_id": event[f"{opp_pre}_on_api_id"],
                    "opp_team_on": event[f"{opp_pre}_on"],
                    "opp_team_on_positions": event[f"{opp_pre}_on_positions"],
                    "opp_forwards_eh_id": event[f"{opp_pre}_forwards_eh_id"],
                    "opp_forwards_api_id": event[f"{opp_pre}_forwards_api_id"],
                    "opp_forwards": event[f"{opp_pre}_forwards"],
                    "opp_forwards_count": event[f"{opp_pre}_forwards_count"],
                    "opp_forwards_percent": event[f"{opp_pre}_forwards_percent"],
                    "opp_defense_eh_id": event[f"{opp_pre}_defense_eh_id"],
                    "opp_defense_api_id": event[f"{opp_pre}_defense_api_id"],
                    "opp_defense": event[f"{opp_pre}_defense"],
                    "opp_defense_count": event[f"{opp_pre}_defense_count"],
                    "opp_goalie_eh_id": event[f"{opp_pre}_goalie_eh_id"],
                    "opp_goalie_api_id": event[f"{opp_pre}_goalie_api_id"],
                    "opp_goalie": event[f"{opp_pre}_goalie"],
                }
            )
            if event.get("opp_strength_state") is None and event["strength_state"] == "ILLEGAL":
                event["opp_strength_state"] = "ILLEGAL"

            event["danger"], event["high_danger"] = 0, 0
            if event.get("coords_x") is not None and event.get("coords_y") is not None and event["coords_x"] != "":
                cx, cy = event["coords_x"], event["coords_y"]
                is_fen = event["event"] in ["GOAL", "SHOT", "MISS"]
                bad_s = event.get("shot_type", "WRIST") not in [
                    "TIP-IN",
                    "WRAP-AROUND",
                    "WRAP",
                    "DEFLECTED",
                    "BAT",
                    "BETWEEN LEGS",
                    "POKE",
                ]

                if is_fen and event.get("pbp_distance", 0) > 89 and bad_s and event.get("zone") != "OFF":
                    mx = abs(cx) + 89 if cx < 0 else cx + 89
                    event["event_distance"] = (mx**2 + cy**2) ** 0.5
                    event["event_angle"] = np.degrees(abs(np.arctan(cy / mx))) if mx != 0 else 90
                else:
                    event["event_distance"] = ((89 - abs(cx)) ** 2 + cy**2) ** 0.5
                    event["event_angle"] = (
                        np.degrees(abs(np.arctan(cy / (89 - abs(cx))))) if (89 - abs(cx)) != 0 else 90
                    )

                if is_fen and event.get("zone") == "DEF" and event.get("event_distance", 0) <= 64:
                    event["zone"] = "OFF"

                if is_fen and event.get("zone") == "OFF":
                    pt = Point(cx, cy)
                    if hd1.contains(pt) or hd2.contains(pt):
                        event["high_danger"] = 1
                    elif d1.contains(pt) or d2.contains(pt):
                        event["danger"] = 1

            if event["event"] == "CHANGE":
                change_key = (event["period"], event["game_seconds"])
                faceoff_event = faceoff_events.get(change_key)

                if faceoff_event:
                    fac_zone = faceoff_event["zone"]
                    fac_team = faceoff_event["event_team"]
                    fac_coords_x = faceoff_event["coords_x"]
                    fac_coords_y = faceoff_event["coords_y"]

                    event["coords_x"], event["coords_y"] = fac_coords_x, fac_coords_y
                    event["zone_start"] = (
                        fac_zone
                        if event["event_team"] == fac_team
                        else {"OFF": "DEF", "DEF": "OFF", "NEU": "NEU"}.get(fac_zone or "")
                    )

                    if abs(fac_coords_x) <= 25:
                        event["zone_start"] = "NEU"

                    event["zone"] = event["zone_start"]
                    # if change_game_seconds in [0, 1200, 2400, 3600, 4800, 6000, 7200, 8400] and fac_zone == "NEU":
                    #     event["zone_start"] = None

                else:
                    event["zone_start"] = "OTF"

            for d in ["block", "change", "chl", "fac", "give", "goal", "hit", "miss", "penl", "shot", "stop", "take"]:
                event[d] = 1 if event["event"].lower() == d else 0

            event["shot"] = 1 if event["event"] in ["GOAL", "SHOT"] else 0
            event["fenwick"] = 1 if event["event"] in ["GOAL", "SHOT", "MISS"] else 0
            event["corsi"] = 1 if event["event"] in ["GOAL", "SHOT", "MISS", "BLOCK"] else 0

            event["hd_goal"] = 1 if event["goal"] and event["high_danger"] else 0
            event["hd_shot"] = 1 if event["shot"] and event["high_danger"] else 0
            event["hd_miss"] = 1 if event["miss"] and event["high_danger"] else 0
            event["hd_fenwick"] = 1 if event["fenwick"] and event["high_danger"] else 0

            event["ozf"] = 1 if event["event"] == "FAC" and event.get("zone") == "OFF" else 0
            event["dzf"] = 1 if event["event"] == "FAC" and event.get("zone") == "DEF" else 0
            event["nzf"] = 1 if event["event"] == "FAC" and event.get("zone") == "NEU" else 0

            z_start = event.get("zone_start")
            event["ozc"] = 1 if event["event"] == "CHANGE" and z_start == "OFF" else 0
            event["dzc"] = 1 if event["event"] == "CHANGE" and z_start == "DEF" else 0
            event["nzc"] = 1 if event["event"] == "CHANGE" and z_start == "NEU" else 0
            event["otf"] = 1 if event["event"] == "CHANGE" and z_start == "OTF" else 0

            for p_len in [0, 2, 4, 5, 10]:
                event[f"pen{p_len}"] = (
                    1 if event["event"] in ["PENL", "DELPEN"] and event.get("penalty_length") == p_len else 0
                )

            if event["event"] == "BLOCK" and "BLOCKED BY TEAMMATE" in str(event.get("description", "")):
                event["teammate_block"], event["block"] = 1, 0
            else:
                event["teammate_block"] = 0

            event["event_idx"] = idx + 1
            nxt_idx = min(idx + 1, len(merged_events) - 1)
            event["event_length"] = merged_events[nxt_idx]["game_seconds"] - event["game_seconds"]
            event["id"] = int(f"{self.game_id}{event['event_idx']:04d}")

            prev_event_type, prev_event_team = event["event"], event["event_team"]

        return merged_events

    def _calculate_pbp_xg(self, events: list) -> tuple:
        """Finalized xG Worker: O(N) sequential calculation. Refactored for maximum readability and streamlined dictionary mapping."""
        # --- 1. Configuration & Constants ---
        model_groups = {
            "even": {"5v5", "4v4", "3v3"},
            "powerplay": {"5v4", "4v3", "5v3"},
            "shorthanded": {"4v5", "3v4", "3v5"},
            "empty_for": {"Ev5", "Ev4", "Ev3"},
            "empty_against": {"5vE", "4vE", "3vE"},
        }

        eligible_strength_states = {
            "5v5",
            "4v4",
            "3v3",
            "5v4",
            "5v3",
            "Ev5",
            "5vE",
            "4v5",
            "4v3",
            "4vE",
            "Ev4",
            "3v5",
            "3v4",
            "Ev3",
            "3vE",
        }

        group_to_model = {
            "even": self._es_model,
            "powerplay": self._pp_model,
            "shorthanded": self._sh_model,
            "empty_for": self._ef_model,
            "empty_against": self._ea_model,
        }

        base_columns = [
            "season",
            "period",
            "period_seconds",
            "score_diff",
            "danger",
            "high_danger",
            "event_distance",
            "event_angle",
            "is_home",
            "position_f",
            "position_d",
            "position_g",
            "seconds_since_last",
            "distance_from_last",
            "prior_shot_same",
            "prior_miss_same",
            "prior_block_same",
            "prior_give_same",
            "prior_take_same",
            "prior_hit_same",
            "prior_shot_opp",
            "prior_miss_opp",
            "prior_block_opp",
            "prior_give_opp",
            "prior_take_opp",
            "prior_hit_opp",
            "prior_face",
            "is_rebound",
            "rush_attempt",
            "backhand",
            "bat",
            "between_legs",
            "cradle",
            "deflected",
            "poke",
            "slap",
            "snap",
            "tip_in",
            "wrap_around",
            "wrist",
        ]

        valid_shots = {
            "backhand",
            "bat",
            "between_legs",
            "cradle",
            "deflected",
            "poke",
            "slap",
            "snap",
            "tip_in",
            "wrap_around",
            "wrist",
        }
        valid_priors = {"SHOT", "MISS", "BLOCK", "GIVE", "TAKE", "HIT"}
        important_events = {"SHOT", "FAC", "HIT", "BLOCK", "MISS", "GIVE", "TAKE", "GOAL"}
        fenwick_events = {"GOAL", "SHOT", "MISS"}

        # --- Pass 1: Feature construction + collect pending predictions (sequential: last_xg_ev state) ---
        pending: dict[str, list] = {group: [] for group in group_to_model}
        last_xg_ev = None

        for play_idx, play in enumerate(events):
            play["pred_goal"] = 0.0

            # Sanitization & Eligibility
            raw_shot = play.get("shot_type") or ""
            s_type = raw_shot.lower().replace("-", "_").replace(" ", "_")
            if s_type not in valid_shots:
                s_type = "wrist"

            is_xg_eligible = (
                play["event"] in important_events
                and play.get("strength_state") in eligible_strength_states
                and play.get("coords_x") is not None
                and play["coords_x"] != ""
                and play.get("coords_y") is not None
                and play["coords_y"] != ""
            )

            if is_xg_eligible:
                # Feature Construction
                xg = {col: 0 for col in base_columns}
                xg.update(
                    {
                        "season": self.season,
                        "period": play["period"],
                        "period_seconds": play["period_seconds"],
                        "score_diff": max(-4, min(4, play.get("score_diff", 0))),
                        "danger": play.get("danger", 0),
                        "high_danger": play.get("high_danger", 0),
                        "event_distance": play.get("event_distance", 0.0),
                        "event_angle": play.get("event_angle", 0.0),
                        "is_home": play.get("is_home", 0),
                    }
                )

                pos = play.get("player_1_position")
                if pos in {"L", "C", "R", "F"}:
                    xg["position_f"] = 1
                elif pos == "D":
                    xg["position_d"] = 1
                elif pos == "G":
                    xg["position_g"] = 1

                if s_type:
                    xg[s_type] = 1

                if last_xg_ev and last_xg_ev["period"] == play["period"]:
                    sec_since = play["game_seconds"] - last_xg_ev["game_seconds"]
                    s_tm = play["event_team"] == last_xg_ev["event_team"]
                    l_ev = last_xg_ev["event"]

                    xg.update(
                        {
                            "seconds_since_last": sec_since,
                            "distance_from_last": (
                                (play["coords_x"] - last_xg_ev["coords_x"]) ** 2
                                + (play["coords_y"] - last_xg_ev["coords_y"]) ** 2
                            )
                            ** 0.5,
                            "prior_face": 1 if l_ev == "FAC" else 0,
                            "is_rebound": 1
                            if (l_ev in {"SHOT", "MISS", "BLOCK"} and sec_since <= 3 and s_tm == (l_ev != "BLOCK"))
                            else 0,
                            "rush_attempt": 1 if (sec_since <= 4 and last_xg_ev.get("zone") == "NEU") else 0,
                        }
                    )

                    if l_ev in valid_priors:
                        xg[f"prior_{l_ev.lower()}_{'same' if s_tm else 'opp'}"] = 1

                ss = play.get("strength_state", "5v5")
                active_group = next((gn for gn, strs in model_groups.items() if ss in strs), None)

                if play["event"] in fenwick_events and active_group:
                    for s in model_groups[active_group]:
                        xg[f"strength_state_{s}"] = 1 if ss == s else 0

                    # Validates exact columns and strips unassigned optional strength dummies
                    val_xg = XGFields.model_validate(xg).model_dump(exclude_unset=True)
                    feature_row = np.array(list(val_xg.values()))
                    pending[active_group].append((play_idx, feature_row, s_type))

                last_xg_ev = play

        # --- Pass 2: Batched predictions per model group ---
        for group, rows in pending.items():
            if not rows:
                continue
            indices, feature_rows, s_types = zip(*rows, strict=True)
            probs = group_to_model[group].predict_proba(np.vstack(feature_rows))[:, 1]
            for _idx, prob, s_type in zip(indices, probs, s_types, strict=True):
                play_idx = int(_idx)  # zip(*rows) loses int type; re-cast explicitly
                events[play_idx]["pred_goal"] = float(prob)
                events[play_idx]["shot_type"] = s_type.upper().replace("_", "-") if s_type else "WRIST"

        # --- Pass 3: Extended on-ice columns + schema validation ---
        final_pbp, final_ext = [], []
        for play in events:
            for (src_name, src_eh, src_api, src_pos), col_group in zip(_EXT_SOURCE_KEYS, _EXT_TARGET_KEYS, strict=True):
                raw_players = play.get(src_name)
                raw_eh_ids = play.get(src_eh)
                raw_api_ids = play.get(src_api)
                raw_positions = play.get(src_pos)

                if "change" in src_name:
                    players = (
                        raw_players
                        if isinstance(raw_players, list)
                        else str(raw_players).split(", ")
                        if raw_players
                        else []
                    )
                    eh_ids = (
                        raw_eh_ids
                        if isinstance(raw_eh_ids, list)
                        else str(raw_eh_ids).split(", ")
                        if raw_eh_ids
                        else []
                    )
                    api_ids = (
                        raw_api_ids
                        if isinstance(raw_api_ids, list)
                        else str(raw_api_ids).split(", ")
                        if raw_api_ids
                        else []
                    )
                    positions = (
                        raw_positions
                        if isinstance(raw_positions, list)
                        else str(raw_positions).split(", ")
                        if raw_positions
                        else []
                    )
                else:
                    players = raw_players if isinstance(raw_players, list) else [raw_players] if raw_players else []
                    eh_ids = raw_eh_ids if isinstance(raw_eh_ids, list) else [raw_eh_ids] if raw_eh_ids else []
                    api_ids = raw_api_ids if isinstance(raw_api_ids, list) else [raw_api_ids] if raw_api_ids else []
                    positions = (
                        raw_positions if isinstance(raw_positions, list) else [raw_positions] if raw_positions else []
                    )

                n = len(players)
                for i, (col, col_eh, col_api, col_pos) in enumerate(col_group):
                    if i < n:
                        play[col] = players[i]
                        play[col_eh] = eh_ids[i] if i < len(eh_ids) else None
                        play[col_api] = api_ids[i] if i < len(api_ids) else None
                        play[col_pos] = positions[i] if i < len(positions) else None
                    else:
                        play[col] = play[col_eh] = play[col_api] = play[col_pos] = None

            if play["event"] in fenwick_events or play["event"] == "BLOCK":
                calculate_score_adjustment(play, self._score_adjustments)

            final_pbp.append(PBPEvent.model_validate(play).model_dump())
            final_ext.append(PBPEventExt.model_construct(**play).model_dump())

        return final_pbp, final_ext

    @cached_property
    def _pbp_pipeline(self) -> tuple[list, list]:
        """Hidden Master Pipeline: Orchestrates merging, state tracking, and xG calculation.

        Caches the result as a tuple to serve both PBP and Extended PBP properties instantly.
        """
        prefetch_concurrent(self._fetch_api_data, self._fetch_html_events, self._fetch_html_rosters, self._fetch_shifts)
        api_events = self.api_events
        html_events = self.html_events
        changes = self.changes
        rosters = self.rosters

        actives = {p["team_jersey"]: p for p in self.rosters if p.get("team_jersey") and p.get("status") == "ACTIVE"}

        if not html_events or not api_events:
            return [], []

        # 1. Pipeline Step 1: Merge
        merged_events = self._merge_pbp_events(html_events, api_events, changes, rosters)

        # 2. Pipeline Step 2: Track Game State
        stateful_events = self._track_pbp_state(merged_events, actives)

        # 3. Pipeline Step 3: Calculate xG and Validate
        final_pbp, final_ext = self._calculate_pbp_xg(stateful_events)

        return final_pbp, final_ext

    @property
    def play_by_play(self) -> list:
        """List of events in play-by-play. Each event is a dictionary with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).play_by_play_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            game_date (str):
                Date game was played, e.g., 2020-01-09
            event_idx (int):
                Index ID for event, e.g., 667
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            strength_state (str):
                Strength state, e.g., 5vE
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            opp_team (str):
                Opposing team, e.g., CHI
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            danger (int):
                Whether shot event occurred from danger area, e.g., 0
            high_danger (int):
                Whether shot event occurred from high-danger area, e.g., 0
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_eh_id_api (str):
                Evolving Hockey ID for player_1 from the api_events (for debugging), e.g., PEKKA.RINNE
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_eh_id_api (str | None):
                Evolving Hockey ID for player_2 from the api_events (for debugging), e.g., None
            player_2_api_id (int | None):
                NHL API ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_eh_id_api (str | None):
                Evolving Hockey ID for player_3 from the api_events (for debugging), e.g., None
            player_3_api_id (int | None):
                NHL API ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            score_state (str):
                Score of the game from event team's perspective, e.g., 4v2
            score_diff (int):
                Score differential from event team's perspective, e.g., 2
            forwards_percent (float):
                Percentage of skaters (i.e., excluding goalies) on-ice that play forward positions (e.g., F, C, L, R)
            opp_forwards_percent (float):
                Percentage of opposing skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            event_length (int):
                Time elapsed prior to next event, e.g., 5
            event_distance (float | None):
                Calculated distance of event from goal, e.g, 185.32673849177834
            pbp_distance (int):
                Distance of event from goal from description, e.g., 185
            event_angle (float | None):
                Angle of event towards goal, e.g., 57.52880770915151
            penalty (str | None):
                Name of penalty, e.g., None
            penalty_length (int | None):
                Duration of penalty, e.g., None
            home_score (int):
                Home team's score, e.g., 2
            home_score_diff (int):
                Home team's score differential, e.g., -2
            away_score (int):
                Away team's score, e.g., 4
            away_score_diff (int):
                Away team's score differential, e.g., 2
            is_home (int):
                Whether event team is home, e.g., 0
            is_away (int):
                Whether event is away, e.g., 1
            home_team (str):
                Home team, e.g., CHI
            away_team (str):
                Away team, e.g., NSH
            home_skaters (int):
                Number of home team skaters on-ice (excl. goalies), e.g., 6
            away_skaters (int):
                Number of away team skaters on-ice (excl. goalies), e.g., 5
            home_on (list | str | None):
                Name of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            home_on_eh_id (list | str | None):
                Evolving Hockey IDs of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_on_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            home_on_positions (list | str | None):
                Positions of home team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            away_on (list | str | None):
                Name of away team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            away_on_eh_id (list | str | None):
                Evolving Hockey IDs of away team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            away_on_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            away_on_positions (list | str | None):
                Positions of away team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            event_team_skaters (int | None):
                Number of event team skaters on-ice (excl. goalies), e.g., 5
            teammates (list | str | None):
                Name of event team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            teammates_eh_id (list | str | None):
                Evolving Hockey IDs of event team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            teammates_api_id (list | str | None = None):
                NHL API IDs of event team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            teammates_positions (list | str | None):
                Positions of event team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            own_goalie (list | str | None):
                Name of the event team's goalie, e.g., PEKKA RINNE
            own_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the event team's goalie, e.g., PEKKA.RINNE
            own_goalie_api_id (list | str | None):
                NHL API ID of the event team's goalie, e.g., 8471469
            forwards (list | str | None):
                Name of event team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            forwards_eh_id (list | str | None):
                Evolving Hockey IDs of event team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            forwards_api_id (list | str | None):
                NHL API IDs of event team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            forwards_count (int):
                Number of teammate skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            defense (list | str | None):
                Name of event team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            defense_eh_id (list | str | None):
                Evolving Hockey IDs of event team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            defense_api_id (list | str | None):
                NHL API IDs of event team's skaters on-ice, e.g., 8475218, 8474600
            defense_count (int):
                Number of teammate skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            opp_strength_state (str | None):
                Strength state from opposing team's perspective, e.g., Ev5
            opp_score_state (str | None):
                Score state from opposing team's perspective, e.g., 2v4
            opp_score_diff (int | None):
                Score differential from opposing team's perspective, e.g., -2
            opp_team_skaters (int | None):
                Number of opposing team skaters on-ice (excl. goalies), e.g., 6
            opp_team_on (list | str | None):
                Name of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            opp_team_on_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_team_on_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            opp_team_on_positions (list | str | None):
                Positions of opposing team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            opp_goalie (list | str | None):
                Name of the opposing team's goalie, e.g., None
            opp_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the opposing team's goalie, e.g., None
            opp_goalie_api_id (list | str | None):
                NHL API ID of the opposing team's goalie, e.g., None
            opp_forwards (list | str | None):
                Name of opposing team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            opp_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            opp_forwards_api_id (list | str | None):
                NHL API IDs of opposing team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            opp_forwards_count (int):
                Number of opposing skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            opp_defense (list | str | None):
                Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            opp_defense_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_defense_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979
            opp_defense_count (int):
                Number of opposing skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            home_forwards (list | str | None):
                Name of home team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            home_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of home team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            home_forwards_api_id (list | str | None = None):
                NHL API IDs of home team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            home_forwards_count (int):
                Number of home skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            home_forwards_percent (float):
                Percentage of home skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            home_defense (list | str | None):
                Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            home_defense_eh_id (list | str | None):
                Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_defense_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979
            home_defense_count (int):
                Number of home skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            home_defense_percent (float):
                Percentage of home skaters (i.e., excluding goalies) on-ice that play defensive positions (e.g., D)
            home_goalie (list | str | None):
                Name of the home team's goalie, e.g., None
            home_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the home team's goalie, e.g., None
            home_goalie_api_id (list | str | None):
                NHL API ID of the home team's goalie, e.g., None
            away_forwards (list | str | None):
                Name of away team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            away_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of away team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            away_forwards_api_id (list | str | None):
                NHL API IDs of away team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            away_forwards_count (int):
                Number of away skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            away_forwards_percent (float):
                Percentage of away skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            away_defense (list | str | None):
                Name of away team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            away_defense_eh_id (list | str | None):
                Evolving Hockey IDs of away team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            away_defense_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice, e.g., 8475218, 8474600
            away_defense_count (int):
                Number of away skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            away_defense_percent (float):
                Percentage of away skaters (i.e., excluding goalies) on-ice that play defensive positions (e.g., D)
            away_goalie (list | str | None):
                Name of the away team's goalie, e.g., PEKKA RINNE
            away_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the away team's goalie, e.g., PEKKA.RINNE
            away_goalie_api_id (list | str | None):
                NHL API ID of the away team's goalie, e.g., 8471469
            change_on_count (int | None):
                Number of players on, e.g., None
            change_off_count (int | None):
                Number of players off, e.g., None
            change_on (list | str | None):
                Names of the players on, e.g., None
            change_on_eh_id (list | str | None):
                Evolving Hockey IDs of the players on, e.g., None
            change_on_api_id (list | str | None):
                NHL API IDs of the players on, e.g., None
            change_on_positions (list | str | None):
                Postions of the players on, e.g., None
            change_off (list | str | None):
                Names of the players off, e.g., None
            change_off_eh_id (list | str | None):
                Evolving Hockey IDs of the players off, e.g., None
            change_off_api_id (list | str | None):
                NHL API IDs of the players off, e.g., None
            change_off_positions (list | str | None):
                Positions of the players off, e.g., None
            change_on_forwards_count (int | None):
                Number of forwards changing on, e.g., None
            change_off_forwards_count (int | None):
                Number of forwards off, e.g., None
            change_on_forwards (list | str | None):
                Names of the forwards on, e.g., None
            change_on_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards on, e.g., None
            change_on_forwards_api_id (list | str | None):
                NHL API IDs of the forwards on, e.g., None
            change_off_forwards (list | str | None):
                Names of the forwards off, e.g., None
            change_off_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards off, e.g., None
            change_off_forwards_api_id (list | str | None):
                NHL API IDs of the forwards off, e.g., None
            change_on_defense_count (int | None):
                Number of defense on, e.g., None
            change_off_defense_count (int | None):
                Number of defense off, e.g., None
            change_on_defense (list | str | None):
                Names of the defense on, e.g., None
            change_on_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense on, e.g., None
            change_on_defense_api_id (list | str | None):
                NHL API IDs of the defense on, e.g., None
            change_off_defense (list | str | None):
                Names of the defense off, e.g., None
            change_off_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense off, e.g., None
            change_off_defense_api_id (list | str | None):
                NHL API IDs of the defense off, e.g., None
            change_on_goalie_count (int | None):
                Number of goalies on, e.g., None
            change_off_goalie_count (int | None):
                Number of goalies off, e.g., None
            change_on_goalie (list | str | None):
                Name of goalie on, e.g., None
            change_on_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie on, e.g., None
            change_on_goalie_api_id (list | str | None):
                NHL API ID of the goalie on, e.g., None
            change_off_goalie (list | str | None):
                Name of the goalie off, e.g., None
            change_off_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie off, e.g., None
            change_off_goalie_api_id (list | str | None):
                NHL API ID of the goalie off, e.g., None
            pred_goal (float):
                xG value for a given shot attempt, e.g., 0.489021
            pred_goal_adj (float):
                Score- and venue-adjusted xG value for a given shot attempt,
                e.g., 0.489021
            goal (int):
                Dummy indicator whether event is a goal, e.g., 1
            goal_adj (float):
                Score- and venue-adjusted value for a goal, e.g., 1.0
            hd_goal (int):
                Dummy indicator whether event is a high-danger goal, e.g., 0
            shot (int):
                Dummy indicator whether event is a shot, e.g., 1
            shot_adj (float):
                Score- and venue-adjusted value for a shot, e.g., 1.0
            hd_shot (int):
                Dummy indicator whether event is a high-danger shot, e.g., 0
            miss (int):
                Dummy indicator whether event is a miss, e.g., 0
            miss_adj (float):
                Score- and venue-adjusted value for a missed shot, e.g., 0.0
            hd_miss (int):
                Dummy indicator whether event is a high-danger missed shot, e.g., 0
            fenwick (int):
                Dummy indicator whether event is a fenwick event, e.g., 1
            fenwick_adj (float):
                Score- and venue-adjusted value for a fenwick event, e.g., 1.0
            hd_fenwick (int):
                Dummy indicator whether event is a high-danger fenwick event, e.g., 0
            corsi (int):
                Dummy indicator whether event is a corsi event, e.g., 1
            corsi_adj (float):
                Score- and venue-adjusted value for a corsi event, e.g., 1.0
            block (int):
                Dummy indicator whether event is a block, e.g., 0
            block_adj (float):
                Score- and venue-adjusted value for a blocked shot, e.g., 0.0
            teammate_block (int):
                Dummy indicator whether event is a shot blocked by a teammate, e.g., 0
            teammate_block_adj (float):
                Score- and venue-adjusted value for a shot blocked by a teammate, e.g., 0.0
            hit (int):
                Dummy indicator whether event is a hit, e.g., 0
            give (int):
                Dummy indicator whether event is a give, e.g., 0
            take (int):
                Dummy indicator whether event is a take, e.g., 0
            fac (int):
                Dummy indicator whether event is a faceoff, e.g., 0
            penl (int):
                Dummy indicator whether event is a penalty, e.g., 0
            change (int):
                Dummy indicator whether event is a change, e.g., 0
            stop (int):
                Dummy indicator whether event is a stop, e.g., 0
            chl (int):
                Dummy indicator whether event is a challenge, e.g., 0
            ozf (int):
                Dummy indicator whether event is a offensive zone faceoff, e.g., 0
            nzf (int):
                Dummy indicator whether event is a neutral zone faceoff, e.g., 0
            dzf (int):
                Dummy indicator whether event is a defensive zone faceoff, e.g., 0
            ozc (int):
                Dummy indicator whether event is a offensive zone change, e.g., 0
            nzc (int):
                Dummy indicator whether event is a neutral zone change, e.g., 0
            dzc (int):
                Dummy indicator whether event is a defensive zone change, e.g., 0
            otf (int):
                Dummy indicator whether event is an on-the-fly change, e.g., 0
            pen0 (int):
                Dummy indicator whether event is a penalty, e.g., 0
            pen2 (int):
                Dummy indicator whether event is a minor penalty, e.g., 0
            pen4 (int):
                Dummy indicator whether event is a double minor penalty, e.g., 0
            pen5 (int):
                Dummy indicator whether event is a major penalty, e.g., 0
            pen10 (int):
                Dummy indicator whether event is a game misconduct penalty, e.g., 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.play_by_play

        """
        return self._pbp_pipeline[0]

    @property
    def play_by_play_ext(self) -> list:
        """List of additional columns used for aggregating on-ice statistics.

        Returns:
            id (int):
                Unique play identifier, the equivalent of the game ID and event_idx concatenated
            event_idx (int):
                Index ID for event
            event_on_1 (str | None):
                Player name
            event_on_1_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_1_api_id (int | None):
                ID used for matching NHL API data
            event_on_1_pos (str | None):
                Player position
            event_on_2 (str | None):
                Player name
            event_on_2_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_2_api_id (int | None):
                ID used for matching NHL API data
            event_on_2_pos (str | None):
                Player position
            event_on_3 (str | None):
                Player name
            event_on_3_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_3_api_id (int | None):
                ID used for matching NHL API data
            event_on_3_pos (str | None):
                Player position
            event_on_4 (str | None):
                Player name
            event_on_4_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_4_api_id (int | None):
                ID used for matching NHL API data
            event_on_4_pos (str | None):
                Player position
            event_on_5 (str | None):
                Player name
            event_on_5_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_5_api_id (int | None):
                ID used for matching NHL API data
            event_on_5_pos (str | None):
                Player position
            event_on_6 (str | None):
                Player name
            event_on_6_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_6_api_id (int | None):
                ID used for matching NHL API data
            event_on_6_pos (str | None):
                Player position
            event_on_7 (str | None):
                Player name
            event_on_7_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_7_api_id (int | None):
                ID used for matching NHL API data
            event_on_7_pos (str | None):
                Player position
            opp_on_1 (str | None):
                Player name
            opp_on_1_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_1_api_id (int | None):
                ID used for matching NHL API data
            opp_on_1_pos (str | None):
                Player position
            opp_on_2 (str | None):
                Player name
            opp_on_2_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_2_api_id (int | None):
                ID used for matching NHL API data
            opp_on_2_pos (str | None):
                Player position
            opp_on_3 (str | None):
                Player name
            opp_on_3_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_3_api_id (int | None):
                ID used for matching NHL API data
            opp_on_3_pos (str | None):
                Player position
            opp_on_4 (str | None):
                Player name
            opp_on_4_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_4_api_id (int | None):
                ID used for matching NHL API data
            opp_on_4_pos (str | None):
                Player position
            opp_on_5 (str | None):
                Player name
            opp_on_5_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_5_api_id (int | None):
                ID used for matching NHL API data
            opp_on_5_pos (str | None):
                Player position
            opp_on_6 (str | None):
                Player name
            opp_on_6_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_6_api_id (int | None):
                ID used for matching NHL API data
            opp_on_6_pos (str | None):
                Player position
            opp_on_7 (str | None):
                Player name
            opp_on_7_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_7_api_id (int | None):
                ID used for matching NHL API data
            opp_on_7_pos (str | None):
                Player position
            change_on_1 (str | None):
                Player name
            change_on_1_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_1_api_id (int | None):
                ID used for matching NHL API data
            change_on_1_pos (str | None):
                Player position
            change_on_2 (str | None):
                Player name
            change_on_2_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_2_api_id (int | None):
                ID used for matching NHL API data
            change_on_2_pos (str | None):
                Player position
            change_on_3 (str | None):
                Player name
            change_on_3_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_3_api_id (int | None):
                ID used for matching NHL API data
            change_on_3_pos (str | None):
                Player position
            change_on_4 (str | None):
                Player name
            change_on_4_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_4_api_id (int | None):
                ID used for matching NHL API data
            change_on_4_pos (str | None):
                Player position
            change_on_5 (str | None):
                Player name
            change_on_5_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_5_api_id (int | None):
                ID used for matching NHL API data
            change_on_5_pos (str | None):
                Player position
            change_on_6 (str | None):
                Player name
            change_on_6_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_6_api_id (int | None):
                ID used for matching NHL API data
            change_on_6_pos (str | None):
                Player position
            change_on_7 (str | None):
                Player name
            change_on_7_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_7_api_id (int | None):
                ID used for matching NHL API data
            change_on_7_pos (str | None):
                Player position
            change_off_1 (str | None):
                Player name
            change_off_1_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_1_api_id (int | None):
                ID used for matching NHL API data
            change_off_1_pos (str | None):
                Player position
            change_off_2 (str | None):
                Player name
            change_off_2_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_2_api_id (int | None):
                ID used for matching NHL API data
            change_off_2_pos (str | None):
                Player position
            change_off_3 (str | None):
                Player name
            change_off_3_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_3_api_id (int | None):
                ID used for matching NHL API data
            change_off_3_pos (str | None):
                Player position
            change_off_4 (str | None):
                Player name
            change_off_4_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_4_api_id (int | None):
                ID used for matching NHL API data
            change_off_4_pos (str | None):
                Player position
            change_off_5 (str | None):
                Player name
            change_off_5_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_5_api_id (int | None):
                ID used for matching NHL API data
            change_off_5_pos (str | None):
                Player position
            change_off_6 (str | None):
                Player name
            change_off_6_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_6_api_id (int | None):
                ID used for matching NHL API data
            change_off_6_pos (str | None):
                Player position
            change_off_7 (str | None):
                Player name
            change_off_7_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_7_api_id (int | None):
                ID used for matching NHL API data
            change_off_7_pos (str | None):
                Player position

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.play_by_play_ext

        """
        return self._pbp_pipeline[1]

    @property
    def play_by_play_df(self) -> pd.DataFrame | pl.DataFrame:
        """Pandas Dataframe of play-by-play data.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            game_date (str):
                Date game was played, e.g., 2020-01-09
            event_idx (int):
                Index ID for event, e.g., 667
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            strength_state (str):
                Strength state, e.g., 5vE
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            opp_team (str):
                Opposing team, e.g., CHI
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            danger (int):
                Whether shot event occurred from danger area, e.g., 0
            high_danger (int):
                Whether shot event occurred from high-danger area, e.g., 0
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_eh_id_api (str):
                Evolving Hockey ID for player_1 from the api_events (for debugging), e.g., PEKKA.RINNE
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_eh_id_api (str | None):
                Evolving Hockey ID for player_2 from the api_events (for debugging), e.g., None
            player_2_api_id (int | None):
                NHL API ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_eh_id_api (str | None):
                Evolving Hockey ID for player_3 from the api_events (for debugging), e.g., None
            player_3_api_id (int | None):
                NHL API ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            score_state (str):
                Score of the game from event team's perspective, e.g., 4v2
            score_diff (int):
                Score differential from event team's perspective, e.g., 2
            forwards_percent (float):
                Percentage of skaters (i.e., excluding goalies) on-ice that play forward positions (e.g., F, C, L, R)
            opp_forwards_percent (float):
                Percentage of opposing skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            event_length (int):
                Time elapsed prior to next event, e.g., 5
            event_distance (float | None):
                Calculated distance of event from goal, e.g, 185.32673849177834
            pbp_distance (int):
                Distance of event from goal from description, e.g., 185
            event_angle (float | None):
                Angle of event towards goal, e.g., 57.52880770915151
            penalty (str | None):
                Name of penalty, e.g., None
            penalty_length (int | None):
                Duration of penalty, e.g., None
            home_score (int):
                Home team's score, e.g., 2
            home_score_diff (int):
                Home team's score differential, e.g., -2
            away_score (int):
                Away team's score, e.g., 4
            away_score_diff (int):
                Away team's score differential, e.g., 2
            is_home (int):
                Whether event team is home, e.g., 0
            is_away (int):
                Whether event is away, e.g., 1
            home_team (str):
                Home team, e.g., CHI
            away_team (str):
                Away team, e.g., NSH
            home_skaters (int):
                Number of home team skaters on-ice (excl. goalies), e.g., 6
            away_skaters (int):
                Number of away team skaters on-ice (excl. goalies), e.g., 5
            home_on (list | str | None):
                Name of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            home_on_eh_id (list | str | None):
                Evolving Hockey IDs of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_on_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            home_on_positions (list | str | None):
                Positions of home team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            away_on (list | str | None):
                Name of away team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            away_on_eh_id (list | str | None):
                Evolving Hockey IDs of away team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            away_on_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            away_on_positions (list | str | None):
                Positions of away team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            event_team_skaters (int | None):
                Number of event team skaters on-ice (excl. goalies), e.g., 5
            teammates (list | str | None):
                Name of event team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            teammates_eh_id (list | str | None):
                Evolving Hockey IDs of event team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            teammates_api_id (list | str | None = None):
                NHL API IDs of event team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            teammates_positions (list | str | None):
                Positions of event team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            own_goalie (list | str | None):
                Name of the event team's goalie, e.g., PEKKA RINNE
            own_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the event team's goalie, e.g., PEKKA.RINNE
            own_goalie_api_id (list | str | None):
                NHL API ID of the event team's goalie, e.g., 8471469
            forwards (list | str | None):
                Name of event team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            forwards_eh_id (list | str | None):
                Evolving Hockey IDs of event team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            forwards_api_id (list | str | None):
                NHL API IDs of event team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            forwards_count (int):
                Number of teammate skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            defense (list | str | None):
                Name of event team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            defense_eh_id (list | str | None):
                Evolving Hockey IDs of event team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            defense_api_id (list | str | None):
                NHL API IDs of event team's skaters on-ice, e.g., 8475218, 8474600
            defense_count (int):
                Number of teammate skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            opp_strength_state (str | None):
                Strength state from opposing team's perspective, e.g., Ev5
            opp_score_state (str | None):
                Score state from opposing team's perspective, e.g., 2v4
            opp_score_diff (int | None):
                Score differential from opposing team's perspective, e.g., -2
            opp_team_skaters (int | None):
                Number of opposing team skaters on-ice (excl. goalies), e.g., 6
            opp_team_on (list | str | None):
                Name of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            opp_team_on_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_team_on_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            opp_team_on_positions (list | str | None):
                Positions of opposing team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            opp_goalie (list | str | None):
                Name of the opposing team's goalie, e.g., None
            opp_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the opposing team's goalie, e.g., None
            opp_goalie_api_id (list | str | None):
                NHL API ID of the opposing team's goalie, e.g., None
            opp_forwards (list | str | None):
                Name of opposing team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            opp_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            opp_forwards_api_id (list | str | None):
                NHL API IDs of opposing team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            opp_forwards_count (int):
                Number of opposing skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            opp_defense (list | str | None):
                Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            opp_defense_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_defense_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979
            opp_defense_count (int):
                Number of opposing skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            home_forwards (list | str | None):
                Name of home team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            home_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of home team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            home_forwards_api_id (list | str | None = None):
                NHL API IDs of home team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            home_forwards_count (int):
                Number of home skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            home_forwards_percent (float):
                Percentage of home skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            home_defense (list | str | None):
                Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            home_defense_eh_id (list | str | None):
                Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_defense_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979
            home_defense_count (int):
                Number of home skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            home_defense_percent (float):
                Percentage of home skaters (i.e., excluding goalies) on-ice that play defensive positions (e.g., D)
            home_goalie (list | str | None):
                Name of the home team's goalie, e.g., None
            home_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the home team's goalie, e.g., None
            home_goalie_api_id (list | str | None):
                NHL API ID of the home team's goalie, e.g., None
            away_forwards (list | str | None):
                Name of away team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            away_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of away team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            away_forwards_api_id (list | str | None):
                NHL API IDs of away team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            away_forwards_count (int):
                Number of away skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            away_forwards_percent (float):
                Percentage of away skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            away_defense (list | str | None):
                Name of away team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            away_defense_eh_id (list | str | None):
                Evolving Hockey IDs of away team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            away_defense_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice, e.g., 8475218, 8474600
            away_defense_count (int):
                Number of away skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            away_defense_percent (float):
                Percentage of away skaters (i.e., excluding goalies) on-ice that play defensive positions (e.g., D)
            away_goalie (list | str | None):
                Name of the away team's goalie, e.g., PEKKA RINNE
            away_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the away team's goalie, e.g., PEKKA.RINNE
            away_goalie_api_id (list | str | None):
                NHL API ID of the away team's goalie, e.g., 8471469
            change_on_count (int | None):
                Number of players on, e.g., None
            change_off_count (int | None):
                Number of players off, e.g., None
            change_on (list | str | None):
                Names of the players on, e.g., None
            change_on_eh_id (list | str | None):
                Evolving Hockey IDs of the players on, e.g., None
            change_on_api_id (list | str | None):
                NHL API IDs of the players on, e.g., None
            change_on_positions (list | str | None):
                Postions of the players on, e.g., None
            change_off (list | str | None):
                Names of the players off, e.g., None
            change_off_eh_id (list | str | None):
                Evolving Hockey IDs of the players off, e.g., None
            change_off_api_id (list | str | None):
                NHL API IDs of the players off, e.g., None
            change_off_positions (list | str | None):
                Positions of the players off, e.g., None
            change_on_forwards_count (int | None):
                Number of forwards changing on, e.g., None
            change_off_forwards_count (int | None):
                Number of forwards off, e.g., None
            change_on_forwards (list | str | None):
                Names of the forwards on, e.g., None
            change_on_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards on, e.g., None
            change_on_forwards_api_id (list | str | None):
                NHL API IDs of the forwards on, e.g., None
            change_off_forwards (list | str | None):
                Names of the forwards off, e.g., None
            change_off_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards off, e.g., None
            change_off_forwards_api_id (list | str | None):
                NHL API IDs of the forwards off, e.g., None
            change_on_defense_count (int | None):
                Number of defense on, e.g., None
            change_off_defense_count (int | None):
                Number of defense off, e.g., None
            change_on_defense (list | str | None):
                Names of the defense on, e.g., None
            change_on_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense on, e.g., None
            change_on_defense_api_id (list | str | None):
                NHL API IDs of the defense on, e.g., None
            change_off_defense (list | str | None):
                Names of the defense off, e.g., None
            change_off_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense off, e.g., None
            change_off_defense_api_id (list | str | None):
                NHL API IDs of the defense off, e.g., None
            change_on_goalie_count (int | None):
                Number of goalies on, e.g., None
            change_off_goalie_count (int | None):
                Number of goalies off, e.g., None
            change_on_goalie (list | str | None):
                Name of goalie on, e.g., None
            change_on_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie on, e.g., None
            change_on_goalie_api_id (list | str | None):
                NHL API ID of the goalie on, e.g., None
            change_off_goalie (list | str | None):
                Name of the goalie off, e.g., None
            change_off_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie off, e.g., None
            change_off_goalie_api_id (list | str | None):
                NHL API ID of the goalie off, e.g., None
            pred_goal (float):
                xG value for a given shot attempt, e.g., 0.489021
            pred_goal_adj (float):
                Score- and venue-adjusted xG value for a given shot attempt,
                e.g., 0.489021
            goal (int):
                Dummy indicator whether event is a goal, e.g., 1
            goal_adj (float):
                Score- and venue-adjusted value for a goal, e.g., 1.0
            hd_goal (int):
                Dummy indicator whether event is a high-danger goal, e.g., 0
            shot (int):
                Dummy indicator whether event is a shot, e.g., 1
            shot_adj (float):
                Score- and venue-adjusted value for a shot, e.g., 1.0
            hd_shot (int):
                Dummy indicator whether event is a high-danger shot, e.g., 0
            miss (int):
                Dummy indicator whether event is a miss, e.g., 0
            miss_adj (float):
                Score- and venue-adjusted value for a missed shot, e.g., 0.0
            hd_miss (int):
                Dummy indicator whether event is a high-danger missed shot, e.g., 0
            fenwick (int):
                Dummy indicator whether event is a fenwick event, e.g., 1
            fenwick_adj (float):
                Score- and venue-adjusted value for a fenwick event, e.g., 1.0
            hd_fenwick (int):
                Dummy indicator whether event is a high-danger fenwick event, e.g., 0
            corsi (int):
                Dummy indicator whether event is a corsi event, e.g., 1
            corsi_adj (float):
                Score- and venue-adjusted value for a corsi event, e.g., 1.0
            block (int):
                Dummy indicator whether event is a block, e.g., 0
            block_adj (float):
                Score- and venue-adjusted value for a blocked shot, e.g., 0.0
            teammate_block (int):
                Dummy indicator whether event is a shot blocked by a teammate, e.g., 0
            teammate_block_adj (float):
                Score- and venue-adjusted value for a shot blocked by a teammate, e.g., 0.0
            hit (int):
                Dummy indicator whether event is a hit, e.g., 0
            give (int):
                Dummy indicator whether event is a give, e.g., 0
            take (int):
                Dummy indicator whether event is a take, e.g., 0
            fac (int):
                Dummy indicator whether event is a faceoff, e.g., 0
            penl (int):
                Dummy indicator whether event is a penalty, e.g., 0
            change (int):
                Dummy indicator whether event is a change, e.g., 0
            stop (int):
                Dummy indicator whether event is a stop, e.g., 0
            chl (int):
                Dummy indicator whether event is a challenge, e.g., 0
            ozf (int):
                Dummy indicator whether event is a offensive zone faceoff, e.g., 0
            nzf (int):
                Dummy indicator whether event is a neutral zone faceoff, e.g., 0
            dzf (int):
                Dummy indicator whether event is a defensive zone faceoff, e.g., 0
            ozc (int):
                Dummy indicator whether event is a offensive zone change, e.g., 0
            nzc (int):
                Dummy indicator whether event is a neutral zone change, e.g., 0
            dzc (int):
                Dummy indicator whether event is a defensive zone change, e.g., 0
            otf (int):
                Dummy indicator whether event is an on-the-fly change, e.g., 0
            pen0 (int):
                Dummy indicator whether event is a penalty, e.g., 0
            pen2 (int):
                Dummy indicator whether event is a minor penalty, e.g., 0
            pen4 (int):
                Dummy indicator whether event is a double minor penalty, e.g., 0
            pen5 (int):
                Dummy indicator whether event is a major penalty, e.g., 0
            pen10 (int):
                Dummy indicator whether event is a game misconduct penalty, e.g., 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.play_by_play_df

        """
        return self._finalize_dataframe(data=self.play_by_play, schema=pbp_polars_schema)
