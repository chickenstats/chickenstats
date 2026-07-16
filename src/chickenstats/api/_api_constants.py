from __future__ import annotations

# Maximum batch sizes per endpoint — mirror the SDK's Field(le=N) constraints.
# When chickenstats-api bumps a limit, update the constant here and re-run
# tests/tests_api/test_api_limits.py to confirm alignment.
PBP_MAX_LIMIT: int = 50_000
STATS_MAX_LIMIT: int = 50_000
PRED_GOAL_MAX_LIMIT: int = 100_000
