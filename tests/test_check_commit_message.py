"""The commit format that check_commit_message.py enforces.

git-cliff builds the changelog from commit summaries and drops what it cannot
parse without a word, so a badly formed message fails nowhere and goes missing
from the release notes. The checker refuses it at commit time. These tests pin
the rules, which CONTRIBUTING.md documents under "Commit format".

Like the checker, this file is the same in chickenstats, chickenstats-api and
chickenstats-xg.
"""

import re
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = next(ROOT.glob("scripts/**/check_commit_message.py"))
# The script is not in a package, so it is run from its path, not imported
check = SimpleNamespace(**runpy.run_path(str(SCRIPT)))

SUMMARY = "fix: return 404 for an unknown game"
BODY = "read_game returned None for an id it did not have.\nIt raises a 404 now."
GOOD = f"{SUMMARY}\n\n{BODY}"
SCOPES = ["api", "live-scraper"]


def problems(summary, body=BODY, scopes=None):
    return check.problems(f"{summary}\n\n{body}", scopes)


def refused(text, summary, body=BODY, scopes=None):
    return any(text in problem for problem in problems(summary, body, scopes))


class TestAccepted:
    def test_a_summary_with_a_body(self):
        assert check.problems(GOOD) == []

    @pytest.mark.parametrize("kind", check.TYPES)
    def test_every_type(self, kind):
        assert problems(f"{kind}: return 404 for an unknown game") == []

    def test_a_scope_on_the_list(self):
        assert problems("fix(api): return 404", scopes=SCOPES) == []

    def test_any_scope_when_the_repository_lists_none(self):
        assert problems("fix(anything): return 404", scopes=None) == []

    def test_an_acronym_as_the_first_word(self):
        assert problems("docs: API keys on the welcome page") == []

    def test_a_body_of_paragraphs_and_a_list(self):
        body = f"{BODY}\n\n- read_game\n- read_player\n\nBoth were 500s."
        assert problems(SUMMARY, body) == []

    def test_a_breaking_change_that_says_what_broke(self):
        body = f"{BODY}\n\nBreaking: an unknown id is a 404, not a 500."
        assert problems("fix!: return 404 for an unknown game", body) == []

    def test_a_long_line_that_cannot_be_wrapped(self):
        url = "https://example.com/" + "a" * 80
        command = "    uv run python scripts/check.py --range " + "a" * 60
        assert problems(SUMMARY, f"{BODY}\n\n{url}\n\n{command}") == []

    @pytest.mark.parametrize("word", ["embed", "seed", "bring", "string", "need"])
    def test_an_imperative_that_looks_like_another_tense(self, word):
        assert problems(f"fix: {word} the fixture in the test") == []


class TestWrittenByGitOrCI:
    def test_a_merge(self):
        assert check.problems("Merge pull request #22 from org/v0.1.8") == []

    def test_a_revert(self):
        assert check.problems(f'Revert "{SUMMARY}"') == []

    def test_a_fixup(self):
        assert check.problems(f"fixup! {SUMMARY}") == []

    def test_a_commit_ci_made(self):
        assert check.problems("chore: sync version to 1.9.0 [skip ci]") == []


class TestWhatGitStrips:
    def test_comments_are_not_the_message(self):
        assert check.problems(f"{GOOD}\n# Please enter the message") == []

    def test_the_diff_from_commit_verbose_is_not_the_message(self):
        scissors = "# ------------------------ >8 ------------------------"
        diff = "diff --git a/x b/x\n+Co-Authored-By: someone"
        assert check.problems(f"{GOOD}\n{scissors}\n{diff}") == []

    def test_only_comments_is_an_empty_message(self):
        assert check.problems("# nothing yet\n") == ["the message is empty"]


class TestTheSummary:
    def test_no_type(self):
        assert refused("type(scope)!: subject", "return 404 for an unknown game")

    def test_a_capitalised_type(self):
        assert refused("type(scope)!: subject", "Fix: return 404")

    def test_no_space_after_the_colon(self):
        assert refused("type(scope)!: subject", "fix:return 404")

    def test_the_bang_before_the_scope(self):
        assert refused("type(scope)!: subject", "fix!(api): return 404")

    def test_a_type_that_is_not_one_of_the_ten(self):
        assert refused("`cost` is not a type", "cost: delete old images")

    def test_a_scope_that_is_not_on_the_list(self):
        summary = "fix(live_scraper): return 404"
        assert refused("`live_scraper` is not a scope", summary, scopes=SCOPES)

    def test_longer_than_the_limit(self):
        assert refused("the limit is 72", "fix: " + "x" * 72)

    def test_exactly_at_the_limit(self):
        assert problems("fix: " + "x" * 67) == []

    def test_a_trailing_period(self):
        assert refused("ends with a period", "fix: return 404.")

    def test_a_capitalised_subject(self):
        assert refused("capital letter", "fix: Return 404")


class TestASubjectThatSaysNothing:
    @pytest.mark.parametrize("subject", ["wip", "misc", "update", "fix bug", "cleanup"])
    def test_one_vague_word(self, subject):
        assert refused("does not say what changed", f"chore: {subject}")

    @pytest.mark.parametrize("verb", ["update", "fix", "change", "refactor", "edit"])
    def test_a_verb_and_a_file_name(self, verb):
        assert refused("does not say what changed", f"fix: {verb} helpers.py")

    def test_a_file_name_in_a_subject_that_says_what_changed(self):
        assert problems("ci: read the commit types from cliff.toml") == []


class TestImperativeMood:
    def test_the_past_tense(self):
        assert refused("not in the past tense", "feat: added the rollup")

    def test_the_gerund(self):
        assert refused("not as `-ing`", "feat: adding the rollup")

    def test_the_third_person(self):
        assert refused("not in the third person", "feat: adds the rollup")


class TestTheBody:
    def test_no_body(self):
        assert any("no body" in p for p in check.problems(SUMMARY))

    def test_a_body_of_trailers_only(self):
        assert refused("no body", SUMMARY, "Refs: #12")

    def test_no_blank_line_before_the_body(self):
        found = check.problems(f"{SUMMARY}\n{BODY}")
        assert any("second line must be blank" in p for p in found)

    def test_a_line_that_was_not_wrapped(self):
        assert refused("longer than 72", SUMMARY, "word " * 20)


class TestBreakingChanges:
    def test_a_bang_with_no_breaking_paragraph(self):
        assert refused("needs a `Breaking:` paragraph", "fix!: return 404")

    def test_a_breaking_paragraph_with_no_bang(self):
        body = f"{BODY}\n\nBreaking: an unknown id is a 404."
        assert refused("needs `!`", SUMMARY, body)


class TestCredit:
    def test_a_co_author_trailer(self):
        body = f"{BODY}\n\nCo-Authored-By: Someone <someone@example.com>"
        assert refused("credits", SUMMARY, body)

    def test_a_line_saying_an_assistant_wrote_it(self):
        assert refused("credits", SUMMARY, f"{BODY}\n\nGenerated with Copilot.")

    def test_an_assistant_named_after_an_adjective(self):
        assert refused("credits", SUMMARY, f"{BODY}\n\nWritten by an AI.")

    def test_a_noreply_address_of_an_assistant(self):
        body = f"{BODY}\n\nSigned-off-by: bot <noreply@anthropic.com>"
        assert refused("credits", SUMMARY, body)

    def test_a_file_named_after_a_tool_is_not_credit(self):
        assert problems(SUMMARY, f"{BODY}\n\nCLAUDE.md repeats the rules.") == []

    def test_regenerated_with_is_not_generated_with(self):
        body = "CHANGELOG.md is regenerated with the new config."
        assert problems(SUMMARY, body) == []

    def test_a_file_generated_by_a_program_is_not_credit(self):
        body = "CHANGELOG.md is generated by git-cliff from commit subjects."
        assert problems(SUMMARY, body) == []


class TestWarnings:
    def test_a_clean_message_has_none(self):
        assert check.warnings(GOOD) == []

    def test_and_in_the_summary(self):
        found = check.warnings(f"fix: return 404 and log the id\n\n{BODY}")
        assert any('"and"' in warning for warning in found)

    def test_an_ampersand_is_not_and(self):
        assert check.warnings(f"docs: restructure the README & guide\n\n{BODY}") == []

    def test_filler_in_the_body(self):
        body = "This commit adds a robust and comprehensive check."
        found = check.warnings(f"{SUMMARY}\n\n{body}")
        assert any("comprehensive" in warning for warning in found)

    def test_a_warning_does_not_refuse_the_commit(self):
        body = "This commit adds a robust check."
        assert check.problems(f"{SUMMARY}\n\n{body}") == []


class TestTheScopesFile:
    def test_it_is_read_from_beside_the_script(self):
        scopes = check.allowed_scopes()
        if scopes is None:
            pytest.skip("this repository lists no scopes")
        assert scopes and all(re.fullmatch(r"[a-z0-9_-]+", s) for s in scopes)

    def test_contributing_names_every_scope(self):
        scopes = check.allowed_scopes() or []
        text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        missing = [scope for scope in scopes if f"`{scope}`" not in text]
        assert not missing, f"CONTRIBUTING.md does not list {missing}"


class TestTheTypesMatchTheChangelog:
    def test_git_cliff_parses_every_type(self):
        """A type git-cliff does not parse is dropped from the changelog."""
        config = ROOT / "cliff.toml"
        if not config.exists():
            config = ROOT / "pyproject.toml"
        parsers = re.findall(r'message = "\^\(?([a-z|]+)\)?"', config.read_text())
        parsed = {kind for group in parsers for kind in group.split("|")}
        assert parsed == set(check.TYPES)
