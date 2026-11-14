import warnings

import pytest

from chickenstats._deprecation import warn_deprecated


def public_function(**kwargs):
    warn_deprecated("old()", since="1.9.0", removed_in="2.0.0", **kwargs)


def test_warn_deprecated_names_the_releases_and_the_replacement():
    with pytest.warns(FutureWarning) as caught:
        public_function(instead="new()")

    assert str(caught[0].message) == (
        "old() is deprecated since chickenstats 1.9.0 and will be removed in 2.0.0. Use new() instead."
    )


def test_warn_deprecated_without_a_replacement():
    with pytest.warns(FutureWarning) as caught:
        public_function()

    assert str(caught[0].message) == "old() is deprecated since chickenstats 1.9.0 and will be removed in 2.0.0."


def test_warn_deprecated_points_at_the_callers_code():
    with pytest.warns(FutureWarning) as caught:
        public_function()

    assert caught[0].filename == __file__


def test_warn_deprecated_is_shown_outside_main():
    """Python's default filters would hide a DeprecationWarning raised from a team's own module."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.resetwarnings()
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        public_function()

    assert len(caught) == 1
