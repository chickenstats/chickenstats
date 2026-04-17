import importlib
import importlib.resources
import logging
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import cache, lru_cache
from typing import cast

from xgboost import XGBClassifier

from chickenstats.chicken_nhl.validation_pydantic import APIEvent
from chickenstats.utilities.enums import FORWARDS

logger = logging.getLogger(__name__)


def load_model(model_name: str, model_version: str) -> XGBClassifier:
    """Load an xG model from the package's bundled model files.

    Parameters:
        model_name: Model variant, e.g. ``"even-strength"``, ``"powerplay"``.
        model_version: Version string matching the filename suffix, e.g. ``"0.1.1"``.

    Returns:
        Fitted ``XGBClassifier`` loaded from the corresponding ``.json`` file.
    """
    model = XGBClassifier()

    with importlib.resources.as_file(
        importlib.resources.files("chickenstats.chicken_nhl.xg_models").joinpath(f"{model_name}-{model_version}.json")
    ) as file:
        model.load_model(file)

    return model


def load_score_adjustments() -> dict:
    """Load the score-adjustment weight table from the package's bundled pickle file.

    Returns:
        Nested dict keyed by ``strength_state → score_diff → weight_column → float``.
    """
    with (
        importlib.resources.as_file(
            importlib.resources.files("chickenstats.chicken_nhl.score_adjustments").joinpath("score_adjustments.pkl")
        ) as file,
        open(file, "rb") as open_file,
    ):
        score_adjustments = pickle.load(open_file)

    return score_adjustments


def calculate_score_adjustment(play: dict, score_adjustments: dict) -> dict:
    """Apply score-state adjustment weights to a shot/goal/block/miss play.

    Score adjustments correct for the well-known bias where teams trailing by
    multiple goals suppress shot attempts. For each of the eight counting
    columns (``goal``, ``pred_goal``, ``shot``, ``miss``, ``block``,
    ``teammate_block``, ``fenwick``, ``corsi``) a new ``*_adj`` column is
    added whose value equals the raw count multiplied by the appropriate
    home or away weight from ``score_adjustments``.

    Only plays with ``event`` in ``{GOAL, SHOT, MISS, BLOCK}`` are modified;
    all other plays are returned unchanged. Score differentials are clamped to
    [-3, 3] before the lookup.
    """
    eligible_strength_states = {"5v5", "4v4", "3v3", "5v4", "5v3", "4v5", "4v3", "3v5", "3v4"}

    if play["event"] in ["GOAL", "SHOT", "MISS", "BLOCK"]:
        if play["home_score_diff"] < -3:
            home_score_diff = -3
        elif play["home_score_diff"] > 3:
            home_score_diff = 3
        else:
            home_score_diff = play["home_score_diff"]

        if play["event"] == "BLOCK" and play["teammate_block"] == 0:
            event_team = play["opp_team"]
        else:
            event_team = play["event_team"]

        is_home = 1 if event_team == play["home_team"] else 0

        adjusted_columns = ["goal", "pred_goal", "shot", "miss", "block", "teammate_block", "fenwick", "corsi"]

        for adjusted_column in adjusted_columns:
            if play["strength_state"] in ["4v5", "3v5", "3v4"]:
                is_home = 0 if is_home == 1 else 1
                strength_state = play["strength_state"][::-1]

            else:
                strength_state = play["strength_state"]

            if is_home == 1:
                weight_column = f"home_{adjusted_column}_weight"
            else:
                weight_column = f"away_{adjusted_column}_weight"

            if adjusted_column == "miss":
                weight_column = weight_column.replace(adjusted_column, "fenwick")

            if adjusted_column == "block":
                weight_column = weight_column.replace(adjusted_column, "corsi")

            if adjusted_column == "teammate_block":
                weight_column = weight_column.replace(adjusted_column, "corsi")

            if strength_state in eligible_strength_states:
                play[f"{adjusted_column}_adj"] = (
                    score_adjustments[strength_state][home_score_diff][weight_column] * play[adjusted_column]
                )

            else:
                play[f"{adjusted_column}_adj"] = play[adjusted_column] * 1

    return play


def _return_name_html(info: str) -> str:
    """Fixes names from HTML endpoint. Method originally published by Harry Shomer.

    In the PBP HTML the name is in a format like: 'Center - MIKE RICHARDS'
    Some also have a hyphen in their last name so can't just split by '-'

    Used for consistency with other data providers.
    """
    s = info.index("-")  # Find first hyphen
    return info[s + 1 :].strip(" ")  # The name should be after the first hyphen


def hs_strip_html(td: list) -> list:
    """Strips HTML code from HTML endpoints. Methodology originally published by Harry Shomer.

    Parses HTML for HTML events function
    """
    if not isinstance(td, list):
        td = list(td)

    for y in range(len(td)):
        # Get the 'br' tag for the time column...this gets us time remaining instead of elapsed and remaining combined
        if y == 3:
            td[y] = td[y].get_text()  # This gets us elapsed and remaining combined-< 3:0017:00
            index = td[y].find(":")
            td[y] = td[y][: index + 3]
        elif (y == 6 or y == 7) and td[0] != "#":  # no cover: start
            # 6 & 7-> These are the player 1 ice one's
            # The second statement controls for when it's just a header
            baz = td[y].find_all("td")
            bar = [
                baz[z] for z in range(len(baz)) if z % 4 != 0
            ]  # Because of previous step we get repeats...delete some

            # The setup in the list is now: Name/Number->Position->Blank...and repeat
            # Now strip all the HTML
            players = []
            for i in range(len(bar)):
                if i % 3 == 0:
                    try:
                        name = _return_name_html(bar[i].find("font")["title"])
                        number = bar[i].get_text().strip("\n")  # Get number and strip leading/trailing newlines
                    except KeyError:
                        name = ""
                        number = ""
                elif i % 3 == 1 and name != "":
                    position = bar[i].get_text()
                    players.append([name, number, position])

            td[y] = players  # no cover: stop
        else:
            td[y] = td[y].get_text()

    return td


model_version = "0.1.1"


@cache
@lru_cache(maxsize=5)
def _get_model(variant: str, version: str) -> XGBClassifier:
    """Cached wrapper around ``load_model`` — loads each variant/version pair once."""
    return load_model(variant, version)


@lru_cache(maxsize=1)
def _get_score_adjustments() -> dict:
    """Cached wrapper around ``load_score_adjustments`` — loads the table once per process."""
    return load_score_adjustments()


# Pre-computed column name tuples for extended on-ice columns — avoids f-string formatting per play
_EXT_SOURCE_KEYS = (
    ("teammates", "teammates_eh_id", "teammates_api_id", "teammates_positions"),
    ("opp_team_on", "opp_team_on_eh_id", "opp_team_on_api_id", "opp_team_on_positions"),
    ("change_on", "change_on_eh_id", "change_on_api_id", "change_on_positions"),
)

_EXT_TARGET_KEYS = tuple(
    tuple((f"{prefix}_{i}", f"{prefix}_{i}_eh_id", f"{prefix}_{i}_api_id", f"{prefix}_{i}_pos") for i in range(1, 8))
    for prefix in ("event_on", "opp_on", "change_on")
)


def handle_scoring_details(event_type: str, event_details: dict) -> dict:
    """Extracts common data for shots and goals."""
    mapping = {
        "event": "SHOT"
        if event_type == "shot-on-goal"
        else "MISS"
        if event_type in ["missed-shot", "failed-shot-attempt"]
        else "GOAL",
        "player_1_api_id": event_details.get("shootingPlayerId") or event_details.get("scoringPlayerId"),
        "player_1_type": "SHOOTER" if "shot" in event_type else "GOAL SCORER",
        "opp_goalie_api_id": event_details.get("goalieInNetId"),
        "shot_type": event_details.get("shotType", "WRIST").upper(),
    }

    if event_type == "goal":
        mapping.update(
            {
                "player_2_api_id": event_details.get("assist1PlayerId"),
                "player_2_type": "PRIMARY ASSIST" if event_details.get("assist1PlayerId") else None,
                "player_3_api_id": event_details.get("assist2PlayerId"),
                "player_3_type": "SECONDARY ASSIST" if event_details.get("assist2PlayerId") else None,
            }
        )
    elif event_type == "missed-shot":
        mapping["miss_reason"] = event_details.get("reason", "").replace("-", " ").upper()

    return mapping


def handle_penalty_details(event_details: dict) -> dict:
    """Logic for PENL event types, including bench penalties."""
    event_info = {
        "event": "PENL",
        "penalty_type": event_details.get("typeCode"),
        "penalty_reason": event_details.get("descKey", "").upper(),
        "penalty_duration": event_details.get("duration"),
    }

    # Bench penalty logic from original code
    is_bench = (
        event_info["penalty_type"] == "BEN"
        or "HEAD-COACH" in event_info["penalty_reason"]
        or "TEAM-STAFF" in event_info["penalty_reason"]
    )
    if is_bench and not event_details.get("committedByPlayerId"):
        event_info.update(
            {
                "player_1": "BENCH",
                "player_1_eh_id": "BENCH",
                "player_1_type": "COMMITTED BY",
                "player_2_api_id": event_details.get("servedByPlayerId"),
                "player_2_type": "SERVED BY",
            }
        )
    else:
        event_info.update(
            {
                "player_1_api_id": event_details.get("committedByPlayerId"),
                "player_1_type": "COMMITTED BY",
                "player_2_api_id": event_details.get("drawnByPlayerId") or event_details.get("servedByPlayerId"),
                "player_2_type": "DRAWN BY" if event_details.get("drawnByPlayerId") else "SERVED BY",
            }
        )
        if event_details.get("drawnByPlayerId") and event_details.get("servedByPlayerId"):
            event_info.update({"player_3_api_id": event_details.get("servedByPlayerId"), "player_3_type": "SERVED BY"})

    return event_info


def map_player_metadata(event_info: dict, rosters: dict) -> dict:
    """Injects Roster data (Names, Positions, EH_IDs) into an Event dict using API IDs."""
    for prefix in ["player_1", "player_2", "player_3", "opp_goalie"]:
        api_id = event_info.get(f"{prefix}_api_id")
        if api_id:
            player = rosters.get(api_id)
            if player:
                event_info.update(
                    {
                        prefix: player.get("player_name"),
                        f"{prefix}_eh_id": player.get("eh_id"),
                        f"{prefix}_team_jersey": player.get("team_jersey"),
                        f"{prefix}_position": player.get("position"),
                    }
                )

    # Specific logic for BLOCK team identification
    if event_info.get("event") == "BLOCK" and event_info.get("player_1_team_jersey"):
        event_info["event_team"] = event_info["player_1_team_jersey"][:3]

    elif event_info.get("event") == "BLOCK" and not event_info.get("player_1_team_jersey"):
        event_info["event_team"] = "OTHER"
        event_info["player_1"] = "REFEREE"
        event_info["player_1_eh_id"] = "REFEREE"
        event_info["player_1_api_id"] = None

    return event_info


def apply_event_versioning(event_list: list) -> list:
    """Ensures simultaneous events get unique version numbers and validates with Pydantic."""
    counts = {}
    final_events = []
    for ev in event_list:
        key = (ev["event"], ev["game_seconds"], ev["period"], ev.get("player_1_api_id"))
        counts[key] = counts.get(key, 0) + 1
        ev["version"] = counts[key]
        final_events.append(APIEvent.model_validate(ev).model_dump())
    return final_events


def parse_time(time_str: str) -> int:
    """Converts 'MM:SS' to total seconds."""
    if not time_str:
        return 0
    try:
        m, s = map(int, time_str.split(":"))
        return (m * 60) + s
    except ValueError:
        return 0


def aggregate_players(players: list) -> dict:
    """Group a player list into positional buckets in a single O(N) pass.

    Returns a dict with keys ``"ALL"``, ``"F"``, ``"D"``, ``"G"``. Each value
    is itself a dict with ``count``, ``jerseys``, ``names``, ``eh_ids``,
    ``api_ids``, and ``positions`` arrays. Every player is added to ``"ALL"``
    and to their specific positional bucket (forwards map to ``"F"``; players
    with unrecognized positions are added to ``"ALL"`` only).
    """
    forwards_set = FORWARDS

    agg: dict[str, dict[str, int | list]] = {
        "ALL": {"count": 0, "jerseys": [], "names": [], "eh_ids": [], "api_ids": [], "positions": []},
        "F": {"count": 0, "jerseys": [], "names": [], "eh_ids": [], "api_ids": [], "positions": []},
        "D": {"count": 0, "jerseys": [], "names": [], "eh_ids": [], "api_ids": [], "positions": []},
        "G": {"count": 0, "jerseys": [], "names": [], "eh_ids": [], "api_ids": [], "positions": []},
    }

    for p in players:
        team_jersey, name, eh_id = p.get("team_jersey"), p.get("player_name"), p.get("eh_id")
        api_id, pos = str(p.get("api_id")), p.get("position")

        # Determine specific bucket using O(1) lookups
        bucket = "F" if pos in forwards_set else pos if pos in {"D", "G"} else None

        # Always add to ALL, plus the specific positional bucket
        buckets_to_fill = ["ALL", bucket] if bucket else ["ALL"]

        for b in buckets_to_fill:
            agg[b]["count"] = cast(int, agg[b]["count"]) + 1
            cast(list, agg[b]["jerseys"]).append(team_jersey)
            cast(list, agg[b]["names"]).append(name)
            cast(list, agg[b]["eh_ids"]).append(eh_id)
            cast(list, agg[b]["api_ids"]).append(api_id)
            cast(list, agg[b]["positions"]).append(pos)

    return agg


def prefetch_concurrent(*fetch_tasks) -> None:
    """Run the given fetch tasks concurrently and cache their results.

    Each task is a bound method with its own cache guard, so calling this
    multiple times is safe — already-fetched tasks return immediately.
    """
    with ThreadPoolExecutor(max_workers=len(fetch_tasks)) as executor:
        futures = [executor.submit(task) for task in fetch_tasks]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:  # noqa: BLE001  # pyright: ignore[reportBroadExceptionCaught]
                logger.debug("Prefetch task failed", exc_info=True)
