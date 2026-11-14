from __future__ import annotations

# Maximum batch sizes per endpoint; keep in step with the API's limits
PBP_MAX_LIMIT: int = 50_000
STATS_MAX_LIMIT: int = 50_000
PRED_GOAL_MAX_LIMIT: int = 50_000
RAW_MAX_LIMIT: int = 50_000
"""Shared limit for the raw chicken_nhl endpoints (rosters, shifts, changes, games, players)."""
IDS_MAX_LIMIT: int = 50_000
"""Shared limit for the game ID and play ID endpoints behind the check_* methods."""

# Retries per page, retryable statuses, and the longest wait between tries
PAGE_RETRIES: int = 3
RETRY_STATUSES: frozenset[int] = frozenset({429, 502, 503, 504})
MAX_RETRY_WAIT: float = 60.0

# Connect and read timeouts in seconds; reads allow for a large page
REQUEST_TIMEOUT: tuple[float, float] = (3.05, 60)
