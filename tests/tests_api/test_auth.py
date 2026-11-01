"""The cached login, its file and the browser sign-in page, with the SDK's network calls replaced."""

import sys

import pytest

from chickenstats.api._auth import _callback_page


class TestCallbackPage:
    def test_renders_without_any_web_framework(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "fasthtml", None)
        monkeypatch.setitem(sys.modules, "fasthtml.common", None)

        page = _callback_page("Signed in", "You're signed in", "Close this tab.")

        assert page.startswith("<!doctype html>")
        assert "<title>Signed in</title>" in page
        assert "<p>Close this tab.</p>" in page

    @pytest.mark.parametrize("position", [0, 1, 2])
    def test_escapes_the_text(self, position):
        text = ["title", "heading", "message"]
        text[position] = "<script>"

        assert "<script>" not in _callback_page(*text)
