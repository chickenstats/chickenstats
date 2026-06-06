"""Drift-detection tests — no network required.

Verifies that chickenstats wrapper constants and kwarg names stay aligned
with the underlying chickenstats_api SDK constraints.

Run without credentials: pytest tests/tests_api/test_api_limits.py -v
"""

from __future__ import annotations

import inspect
import typing

import pytest
from pydantic.fields import FieldInfo

import chickenstats_api

from chickenstats.api._api_constants import PBP_MAX_LIMIT, PRED_GOAL_MAX_LIMIT, STATS_MAX_LIMIT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_field_constraints(api_cls, method_name: str, param_name: str) -> dict:
    """Return a dict of constraint-class-name -> attribute dict for one SDK parameter."""
    method = getattr(api_cls, method_name)
    try:
        hints = typing.get_type_hints(method, include_extras=True)
    except Exception:
        return {}
    hint = hints.get(param_name)
    if hint is None:
        return {}
    result: dict = {}
    for top in typing.get_args(hint):  # unwrap Optional
        for meta in typing.get_args(top):  # unwrap Annotated
            if isinstance(meta, FieldInfo):
                for m in meta.metadata:
                    cls_name = type(m).__name__
                    slots = getattr(type(m), "__slots__", ())
                    result[cls_name] = {s: getattr(m, s) for s in slots if hasattr(m, s)}
    return result


def _sdk_params(api_cls, method_name: str) -> set[str]:
    """Return the set of non-internal parameter names the SDK method accepts."""
    sig = inspect.signature(getattr(api_cls, method_name))
    return {p for p in sig.parameters if p not in ("self", "args", "kwargs", "_request_timeout")}


# ---------------------------------------------------------------------------
# Parametrize tables
# ---------------------------------------------------------------------------

_LIMIT_CASES = [
    pytest.param(chickenstats_api.PlayByPlayApi, "read_pbp", PBP_MAX_LIMIT, id="pbp"),
    pytest.param(chickenstats_api.StatsApi, "read_game_stats", STATS_MAX_LIMIT, id="game_stats"),
    pytest.param(chickenstats_api.StatsApi, "read_season_stats", STATS_MAX_LIMIT, id="season_stats"),
    pytest.param(chickenstats_api.TeamStatsApi, "read_game_team_stats", STATS_MAX_LIMIT, id="game_team_stats"),
    pytest.param(chickenstats_api.TeamStatsApi, "read_season_team_stats", STATS_MAX_LIMIT, id="season_team_stats"),
    pytest.param(chickenstats_api.LinesApi, "read_game_lines", STATS_MAX_LIMIT, id="game_lines"),
    pytest.param(chickenstats_api.LinesApi, "read_season_lines", STATS_MAX_LIMIT, id="season_lines"),
    pytest.param(chickenstats_api.RapmApi, "read_rapm", STATS_MAX_LIMIT, id="rapm"),
    pytest.param(chickenstats_api.InferenceApi, "read_pred_goal", PRED_GOAL_MAX_LIMIT, id="pred_goal"),
    pytest.param(chickenstats_api.LiveApi, "read_live_pbp", STATS_MAX_LIMIT, id="live_pbp"),
]

# Kwargs api.py passes to each SDK method (limit and offset are always internal).
_WRAPPER_KWARGS: dict[str, set[str]] = {
    "read_pbp": {
        "season",
        "sessions",
        "game_id",
        "event",
        "player_1",
        "goalie",
        "event_team",
        "opp_team",
        "strength_state",
    },
    "read_game_stats": {
        "season",
        "sessions",
        "game_id",
        "player",
        "api_id",
        "eh_id",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "teammates",
        "opposition",
        "level",
    },
    "read_season_stats": {
        "season",
        "sessions",
        "player",
        "api_id",
        "eh_id",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "teammates",
        "opposition",
    },
    "read_game_team_stats": {
        "season",
        "sessions",
        "game_id",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "level",
    },
    "read_season_team_stats": {"season", "sessions", "team", "opp_team", "strength_state", "score_state"},
    "read_game_lines": {
        "season",
        "sessions",
        "game_id",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "level",
        "linemates",
        "opposition",
    },
    "read_season_lines": {
        "season",
        "sessions",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "linemates",
        "opposition",
    },
    "read_rapm": {"season", "sessions", "api_id", "name", "team", "situation"},
    "read_pred_goal": {"season", "sessions", "game_id"},
    "read_live_pbp": {"game_id"},
}


# ---------------------------------------------------------------------------
# TestLimitConstants — limit upper-bound alignment
# ---------------------------------------------------------------------------


class TestLimitConstants:
    """Verify our per-endpoint limit constants stay within what the SDK allows."""

    @pytest.mark.parametrize("api_cls, method_name, our_limit", _LIMIT_CASES)
    def test_limit_within_sdk_bounds(self, api_cls, method_name, our_limit):
        constraints = _extract_field_constraints(api_cls, method_name, "limit")
        le = constraints.get("Le", {}).get("le")
        ge = constraints.get("Ge", {}).get("ge")
        assert le is not None, f"{api_cls.__name__}.{method_name}: no 'le' constraint on limit"
        assert our_limit <= le, f"{api_cls.__name__}.{method_name}: our constant {our_limit} exceeds SDK le={le}"
        if ge is not None:
            assert our_limit >= ge, f"{api_cls.__name__}.{method_name}: our constant {our_limit} is below SDK ge={ge}"


# ---------------------------------------------------------------------------
# TestSdkFieldConstraints — full constraint schema + kwarg alignment
# ---------------------------------------------------------------------------


class TestSdkFieldConstraints:
    """Verify kwarg names and all Field constraints on controlled params."""

    @pytest.mark.parametrize("api_cls, method_name, our_limit", _LIMIT_CASES)
    def test_kwarg_names_in_sdk_signature(self, api_cls, method_name, our_limit):
        """Every kwarg api.py passes must be a valid SDK parameter name."""
        sdk_params = _sdk_params(api_cls, method_name)
        unknown = _WRAPPER_KWARGS[method_name] - sdk_params
        assert not unknown, (
            f"{api_cls.__name__}.{method_name}: wrapper passes unknown kwargs {unknown}. SDK accepts: {sdk_params}"
        )

    @pytest.mark.parametrize("api_cls, method_name, our_limit", _LIMIT_CASES)
    def test_limit_ge_constraint(self, api_cls, method_name, our_limit):
        """Our limit constant must satisfy the SDK's ge= lower bound."""
        constraints = _extract_field_constraints(api_cls, method_name, "limit")
        ge = constraints.get("Ge", {}).get("ge")
        if ge is not None:
            assert our_limit >= ge, f"{api_cls.__name__}.{method_name}: our constant {our_limit} is below SDK ge={ge}"

    @pytest.mark.parametrize("api_cls, method_name, our_limit", _LIMIT_CASES)
    def test_offset_ge_constraint(self, api_cls, method_name, our_limit):
        """Initial offset of 0 must satisfy the SDK's ge= lower bound on offset."""
        constraints = _extract_field_constraints(api_cls, method_name, "offset")
        if not constraints:
            pytest.skip(f"{api_cls.__name__}.{method_name} has no offset parameter constraints")
        ge = constraints.get("Ge", {}).get("ge")
        if ge is not None:
            assert 0 >= ge, f"{api_cls.__name__}.{method_name}: initial offset=0 is below SDK ge={ge}"

    @pytest.mark.parametrize("api_cls, method_name, our_limit", _LIMIT_CASES)
    def test_no_uncovered_constrained_params(self, api_cls, method_name, our_limit):
        """Flag any SDK params with Field constraints that are not explicitly tested here.

        This test fails when the SDK adds new constraints to pass-through parameters,
        prompting a review of whether they need validation in the wrapper.
        """
        method = getattr(api_cls, method_name)
        sig = inspect.signature(method)
        try:
            hints = typing.get_type_hints(method, include_extras=True)
        except Exception:
            return

        constrained: set[str] = set()
        for param_name in sig.parameters:
            if param_name in ("self", "args", "kwargs", "_request_timeout"):
                continue
            hint = hints.get(param_name)
            if hint is None:
                continue
            for top in typing.get_args(hint):
                for meta in typing.get_args(top):
                    if isinstance(meta, FieldInfo) and meta.metadata:
                        constrained.add(param_name)

        untested = constrained - {"limit", "offset"}
        assert not untested, (
            f"{api_cls.__name__}.{method_name}: these params have SDK Field constraints but are "
            f"not covered by drift-detection tests: {untested}. "
            "Add explicit checks for them in TestSdkFieldConstraints."
        )
