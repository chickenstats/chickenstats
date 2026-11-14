"""Tests for behavior that is known to be wrong today.

Each test states what the correct result is and is marked as an expected failure, with the
exception the bug causes. The marks are strict: when a bug is fixed its test passes, pytest
reports that as a failure, and the test moves to test_fixed_bugs.py in the same commit as the
fix. A test that fails with any other exception is reported, so it cannot pass as expected
for the wrong reason.

All of them run on the saved games, with no network access.
"""

import pytest


def known_bug(reason: str, raises: type[BaseException] | tuple[type[BaseException], ...] = AssertionError):
    """Mark a test as failing today because of a known bug, with the exception that bug causes."""
    return pytest.mark.xfail(strict=True, reason=reason, raises=raises)
