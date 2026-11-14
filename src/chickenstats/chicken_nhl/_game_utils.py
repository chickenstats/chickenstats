"""Shared utilities for the Game mixin classes."""

import importlib.resources
import logging
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import cast

from lxml import etree  # ty: ignore[unresolved-import]
import polars as pl

from chickenstats.chicken_nhl.validation_pydantic import APIEvent
from chickenstats.utilities.enums import FORWARDS

logger = logging.getLogger(__name__)

# Events that belong to neither team
NON_TEAM_EVENTS = frozenset(
    {
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
    }
)

# Shots on goal, unblocked attempts (Fenwick) and all attempts (Corsi)
SHOT_EVENTS = frozenset({"GOAL", "SHOT"})
FENWICK_EVENTS = SHOT_EVENTS | {"MISS"}
CORSI_EVENTS = FENWICK_EVENTS | {"BLOCK"}

# Events whose player_2 plays for the other team: the player hit, the faceoff loser, the blocker
# and the player who drew the penalty
OPPOSING_PLAYER_2_EVENTS = frozenset({"BLOCK", "FAC", "HIT", "PENL"})


def load_score_adjustments() -> dict:
    """Load the score-adjustment weight table from the package's bundled pickle file.

    Returns:
        Nested dict keyed by ``strength_state → score_diff → weight_column → float``.
    """
    import gzip

    with (
        importlib.resources.as_file(
            importlib.resources.files("chickenstats.chicken_nhl.score_adjustments").joinpath("score_adjustments.pkl.gz")
        ) as file,
        gzip.open(file, "rb") as open_file,
    ):
        score_adjustments = pickle.load(open_file)

    return score_adjustments


_ELIGIBLE_STRENGTH_STATES = ("5v5", "4v4", "3v3", "5v4", "5v3", "4v3")
_DISADVANTAGE_STATES = {"4v5": "5v4", "3v5": "5v3", "3v4": "4v3"}

# The table weight each adjusted column uses; a miss takes Fenwick's and a block Corsi's
_WEIGHT_SOURCES = {
    "goal": "goal",
    "shot": "shot",
    "miss": "fenwick",
    "block": "corsi",
    "teammate_block": "corsi",
    "fenwick": "fenwick",
    "corsi": "corsi",
}


def calculate_score_adjustment(play: dict, score_adjustments: dict) -> dict:
    """Apply score-state adjustment weights to a shot/goal/block/miss play.

    Score adjustments correct for the well-known bias where teams trailing by
    multiple goals suppress shot attempts.
    """
    if play["event"] not in CORSI_EVENTS:
        return play

    home_score_diff = max(-3, min(3, play["home_score_diff"]))

    # A blocked shot's event team is the blocking team, so it is weighted from the shooting team's side
    if play["event"] == "BLOCK" and play["teammate_block"] == 0:
        event_team, strength_state = play["opp_team"], play["opp_strength_state"]
    else:
        event_team, strength_state = play["event_team"], play["strength_state"]

    is_home = event_team == play["home_team"]

    # A disadvantage state is looked up through its mirror, from the other team's side
    if strength_state in _DISADVANTAGE_STATES:
        is_home = not is_home
        strength_state = _DISADVANTAGE_STATES[strength_state]

    side = "home" if is_home else "away"
    for column, source in _WEIGHT_SOURCES.items():
        if strength_state in _ELIGIBLE_STRENGTH_STATES:
            play[f"{column}_adj"] = (
                score_adjustments[strength_state][home_score_diff][f"{side}_{source}_weight"] * play[column]
            )
        else:
            play[f"{column}_adj"] = play[column]

    return play


_XG_COLS = ("pred_goal", "base_xg", "context_xg")
_XG_ADJ_COLS = ("pred_goal_adj", "base_xg_adj", "context_xg_adj")
_XG_ADJ_KEY_COLS = ("event_team", "home_team", "home_score_diff", "strength_state")


@lru_cache(maxsize=1)
def _pred_goal_weights() -> pl.DataFrame:
    """The pred_goal weight for each strength state, home score difference and side, from the adjustment table."""
    score_adjustments = load_score_adjustments()

    rows = []
    for strength_state in _ELIGIBLE_STRENGTH_STATES:
        for score_diff, weights in score_adjustments[strength_state].items():
            rows.append((strength_state, score_diff, True, weights["home_pred_goal_weight"]))
            rows.append((strength_state, score_diff, False, weights["away_pred_goal_weight"]))

    return pl.DataFrame(
        rows,
        schema={"_state": pl.String, "_score_diff": pl.Int64, "_is_home": pl.Boolean, "_weight": pl.Float64},
        orient="row",
    )


def prepare_xg(df: pl.DataFrame) -> pl.DataFrame:
    """Null xG outside goals, shots and misses, and fill the score-adjusted xG columns from the raw ones."""
    xg_cols = [x for x in _XG_COLS + _XG_ADJ_COLS if x in df.columns]
    if not xg_cols:
        return df

    is_attempt = pl.col("event").is_in(FENWICK_EVENTS)

    is_shootout = pl.lit(False)
    if "shootout_attempt" in df.columns:
        is_shootout = pl.col("shootout_attempt") == 1

    df = df.with_columns(
        pl.when(is_shootout)
        .then(0.0)
        .when(is_attempt)
        .then(pl.col(c).cast(pl.Float64).fill_nan(None))
        .otherwise(None)
        .alias(c)
        for c in xg_cols
    )

    # An all-null column counts as not supplied
    empty = [c for c in xg_cols if df[c].null_count() == df.height]
    df = df.drop(empty)

    to_adjust = [c for c in _XG_COLS if c in df.columns]
    if not to_adjust or any(c not in df.columns for c in _XG_ADJ_KEY_COLS):
        return df

    disadvantage = pl.col("strength_state").is_in(list(_DISADVANTAGE_STATES))
    keys = df.select(
        _state=pl.when(disadvantage)
        .then(pl.col("strength_state").replace(_DISADVANTAGE_STATES))
        .otherwise(pl.col("strength_state")),
        _score_diff=pl.col("home_score_diff").clip(-3, 3).cast(pl.Int64),
        _is_home=(pl.col("event_team") == pl.col("home_team")).xor(disadvantage),
    )
    weight = keys.join(
        _pred_goal_weights(), on=["_state", "_score_diff", "_is_home"], how="left", maintain_order="left"
    )["_weight"].fill_null(1.0)

    # One set of xG weights; a supplied adjusted value is kept
    adjusted = []
    for column in to_adjust:
        expr = pl.col(column) * weight
        if f"{column}_adj" in df.columns:
            expr = pl.coalesce(f"{column}_adj", expr)
        adjusted.append(expr.alias(f"{column}_adj"))

    return df.with_columns(adjusted)


def is_cut_off(content: bytes) -> bool:
    """Whether an NHL HTML report ended before its closing tag, as one cut off in transit does.

    Older reports wrap the page in an XML element, so the tag is looked for anywhere, not only at the end.
    """
    return b"</html>" not in content.lower()


def decode_report(content: bytes) -> str:
    """Decode an NHL HTML report. They are UTF-8; older ones that are not fall back to Latin-1."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("ISO-8859-1")


def parse_report(content: bytes) -> etree._Element | None:
    """Parse an NHL HTML report with lxml, or return ``None`` if it has no document."""
    try:
        return etree.HTML(decode_report(content).encode("utf-8"), etree.HTMLParser(encoding="utf-8"))
    except (etree.ParserError, etree.XMLSyntaxError):
        return None


def node_text(node: etree._Element) -> str:
    """Return all the text inside an element, in document order."""
    return "".join(node.xpath(".//text()"))


def node_words(node: etree._Element) -> str:
    """Return an element's text pieces, each stripped, joined by single spaces."""
    return " ".join(text for piece in node.xpath(".//text()") if (text := piece.strip()))


@lru_cache(maxsize=1)
def _get_score_adjustments() -> dict:
    """Cached wrapper around ``load_score_adjustments`` — loads the table once per process."""
    return load_score_adjustments()


_POSITION_ORDER: dict[str, int] = {"F": 0, "D": 1, "G": 2}

# Rosters list forwards as C, L and R, so each position code is mapped to its F, D or G group
_POSITION_BUCKETS: dict[str, str] = {**dict.fromkeys(FORWARDS, "F"), "D": "D", "G": "G"}

# Lists kept per bucket by aggregate_players
_AGG_KEYS = ("jerseys", "names", "eh_ids", "api_ids", "positions")


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
                "highlight_clip_url": event_details.get("highlightClipSharingUrl"),
            }
        )
    elif event_type == "missed-shot":
        mapping["miss_reason"] = api_reason(event_details.get("reason"))

    return mapping


def api_reason(code: str | None) -> str | None:
    """Return an API reason code in words, e.g. ``tv-timeout`` as ``TV TIMEOUT``, or None when the feed has none."""
    return code.replace("-", " ").upper() if code else None


def handle_penalty_details(event_details: dict) -> dict:
    """Logic for PENL event types, including bench penalties."""
    event_info = {
        "event": "PENL",
        "penalty_type": event_details.get("typeCode"),
        "penalty_reason": desc_key.upper() if (desc_key := event_details.get("descKey")) else None,
        "penalty_duration": event_details.get("duration"),
    }

    # A bench penalty has no player who committed it
    reason = event_info["penalty_reason"]
    is_bench = event_info["penalty_type"] == "BEN" or (
        reason is not None and ("HEAD-COACH" in reason or "TEAM-STAFF" in reason)
    )
    if is_bench and not event_details.get("committedByPlayerId"):
        event_info.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_type": "COMMITTED BY"})
    else:
        event_info.update(
            {"player_1_api_id": event_details.get("committedByPlayerId"), "player_1_type": "COMMITTED BY"}
        )

    # player_2 drew the penalty and player_3 serves it
    if event_details.get("drawnByPlayerId"):
        event_info.update({"player_2_api_id": event_details.get("drawnByPlayerId"), "player_2_type": "DRAWN BY"})
    if event_details.get("servedByPlayerId"):
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


def overtime_seconds(game_id: int) -> int:
    """Overtime length in seconds, from the game type in the game ID."""
    return {"03": 1200, "20": 1200, "19": 600}.get(str(game_id)[4:6], 300)


def period_length(period: int, overtime: int) -> int:
    """The seconds in a period, given the game's overtime length."""
    return 1200 if period < 4 else overtime


def game_seconds(period: int, period_seconds: int, overtime: int) -> int:
    """Seconds since the start of the game, with a shootout placed at the end of overtime."""
    if period == 5 and overtime < 1200:
        return 3600 + overtime + period_seconds
    return (period - 1) * 1200 + period_seconds


def format_time(seconds: int) -> str:
    """Seconds as the reports' M:SS clock."""
    return f"{seconds // 60}:{seconds % 60:02d}"


def format_duration(seconds: int) -> str:
    """Seconds as the MM:SS the shift reports use for a duration."""
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


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
    """Group a player list into positional buckets.

    Returns a dict with keys ``"ALL"``, ``"F"``, ``"D"``, ``"G"``. Each value
    is itself a dict with ``count``, ``jerseys``, ``names``, ``eh_ids``,
    ``api_ids``, and ``positions`` arrays. Every player is added to ``"ALL"``
    and to their specific positional bucket (forwards map to ``"F"``; players
    with unrecognized positions are added to ``"ALL"`` only).
    """
    agg: dict[str, dict[str, int | list]] = {
        bucket: {"count": 0, **{key: [] for key in _AGG_KEYS}} for bucket in ("ALL", "F", "D", "G")
    }

    for p in players:
        pos = p.get("position")
        values = (p.get("team_jersey"), p.get("player_name"), p.get("eh_id"), str(p.get("api_id")), pos)
        bucket = _POSITION_BUCKETS.get(pos)

        # Always add to ALL, plus the specific positional bucket
        buckets_to_fill = ["ALL", bucket] if bucket else ["ALL"]

        for b in buckets_to_fill:
            agg[b]["count"] = cast(int, agg[b]["count"]) + 1
            for key, value in zip(_AGG_KEYS, values, strict=True):
                cast(list, agg[b][key]).append(value)

    def by_api_id(api_id: str) -> tuple[int, int]:
        # A player with no API ID is stored as "None" and sorts last
        return (0, int(api_id)) if api_id.isdigit() else (1, 0)

    for bucket_name, bucket in agg.items():
        api_ids: list[str] = cast(list, bucket["api_ids"])
        if api_ids:
            positions: list[str] = cast(list, bucket["positions"])
            if bucket_name == "ALL":
                order = sorted(
                    range(len(api_ids)),
                    key=lambda i: (
                        _POSITION_ORDER.get(_POSITION_BUCKETS.get(positions[i], positions[i]), 3),
                        *by_api_id(api_ids[i]),
                    ),
                )
            else:
                order = sorted(range(len(api_ids)), key=lambda i: by_api_id(api_ids[i]))
            for key in _AGG_KEYS:
                bucket[key] = [cast(list, bucket[key])[i] for i in order]

    return agg


def prefetch_concurrent(*fetch_tasks) -> None:
    """Run the given fetch tasks concurrently and cache their results."""
    # Nothing to fetch, and a pool needs at least one worker
    if not fetch_tasks:
        return
    with ThreadPoolExecutor(max_workers=len(fetch_tasks)) as executor:
        futures = [executor.submit(task) for task in fetch_tasks]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:  # noqa: BLE001  # pyright: ignore[reportBroadExceptionCaught]
                # Best effort; property access retries later
                logger.warning("Prefetch task failed", exc_info=True)
