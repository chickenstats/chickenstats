"""Utility helpers for the chickenstats API.

Includes:
    * _to_int_list  — coerce a scalar/list/None parameter to list[int] | None
    * _to_str_list  — coerce a scalar/list/None parameter to list[str] | None
"""

from __future__ import annotations


def _to_int_list(v: list | int | str | None) -> list[int] | None:
    """Coerce a scalar, list, or None query parameter to ``list[int] | None``.

    Parameters:
        v: The raw parameter value — ``None``, a single ``int`` or ``str``, or an
           iterable of values that can each be passed to ``int()``.

    Returns:
        ``None`` when *v* is ``None``; otherwise a ``list[int]``.
    """
    if v is None:
        return None
    if isinstance(v, (int, str)):
        return [int(v)]
    return [int(x) for x in v]


def _to_str_list(v: list | str | None) -> list[str] | None:
    """Coerce a scalar, list, or None query parameter to ``list[str] | None``.

    Parameters:
        v: The raw parameter value — ``None``, a single ``str``, or an iterable of
           strings.

    Returns:
        ``None`` when *v* is ``None``; otherwise a ``list[str]``.
    """
    if v is None:
        return None
    if isinstance(v, str):
        return [v]
    return list(v)
