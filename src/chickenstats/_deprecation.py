"""Warn when a public name, parameter or column is on its way out of the package."""

from __future__ import annotations

import warnings


def warn_deprecated(name: str, *, since: str, removed_in: str, instead: str | None = None, stacklevel: int = 2) -> None:
    """Warn that part of the public surface will be removed, naming the releases and the replacement.

    FutureWarning, not DeprecationWarning: Python hides DeprecationWarning unless the caller is
    ``__main__``, so a team calling chickenstats from its own module would never see it.

    Args:
        name (str):
            What is deprecated, as a user would write it, e.g., ``prep_stats(strengths=...)``.
        since (str):
            The release that deprecated it, e.g., ``1.9.0``.
        removed_in (str):
            The first release without it, e.g., ``2.0.0``.
        instead (str | None):
            What to use in its place. Leave as None if there is no replacement.
        stacklevel (int):
            Frames between this call and the user's code. The default suits a public function that
            calls this directly; add one for each private helper in between.

    Warns:
        FutureWarning: Always.

    Examples:
        Renaming a parameter and keeping the old name for a release:
        >>> warn_deprecated("prep_stats(strengths=...)", since="1.9.0", removed_in="2.0.0", instead="strength_state")
    """
    replacement = f" Use {instead} instead." if instead else ""
    message = f"{name} is deprecated since chickenstats {since} and will be removed in {removed_in}.{replacement}"
    warnings.warn(message, FutureWarning, stacklevel=stacklevel + 1)
