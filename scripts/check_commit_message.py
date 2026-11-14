#!/usr/bin/env python3
"""Check a commit message against the commit format in CONTRIBUTING.md.

A message is a one-line summary, a blank line and a body. The summary feeds the
changelog and the body is for whoever reviews the change. git-cliff cannot
reject a message, so this does.

    check_commit_message.py .git/COMMIT_EDITMSG    as a commit-msg hook
    check_commit_message.py --range main..HEAD     every commit in a range

This file is the same in chickenstats, chickenstats-api and chickenstats-xg.
Change all three together. What differs between them is commit_scopes.txt,
next to this file, which lists the scopes a repository allows.

Standard library only, and nothing newer than Python 3.9.
"""

import re
import subprocess
import sys
from pathlib import Path

MAX_SUMMARY_LENGTH = 72
MAX_BODY_LINE_LENGTH = 72

# The types git-cliff is configured to parse. The first four reach the changelog.
CHANGELOG_TYPES = ("feat", "fix", "perf", "docs")
OTHER_TYPES = ("refactor", "test", "build", "ci", "style", "chore")
TYPES = CHANGELOG_TYPES + OTHER_TYPES

# Messages git writes by itself
EXEMPT_PREFIXES = ("Merge ", "Revert ", "fixup! ", "squash! ", "amend! ")

SUMMARY = re.compile(
    r"""
    ^(?P<type>[a-z]+)
    (\((?P<scope>[^)]*)\))?
    (?P<breaking>!)?
    :\ (?P<subject>\S.*)$
    """,
    re.VERBOSE,
)

TRAILER = re.compile(r"^[A-Za-z][A-Za-z-]*: \S")

BREAKING = re.compile(r"^(Breaking|BREAKING CHANGE):")

# A commit is signed by the person who made it: no co-author line, and no
# line saying an assistant wrote it
ASSISTANT = r"(claude|chatgpt|gpt|copilot|gemini|codex|cursor|an?\ (ai|llm))"
CREDIT = re.compile(
    rf"""
    co-authored-by
    | \b(generated|written|created|assisted)\ (with|by)\ (\S+\ )?{ASSISTANT}\b
    | \b(ai|llm)[- ](generated|assisted|written)\b
    | noreply@(anthropic|openai|github)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# A subject that names no change: one of these words alone, or a verb and a file
VAGUE = re.compile(
    r"""
    ^(updates?|changes?|misc|wip|stuff|fix(es)?|bug\ ?fix(es)?|fix\ bugs?
      |clean\ ?up|tweaks?|improvements?|minor\ (changes|fixes)|refactor)$
    | ^(update|change|modify|edit|fix|tweak|improve|refactor|clean\ up|touch)
      (\ the)?\ \S+\.[a-z]{1,5}$
    """,
    re.VERBOSE | re.IGNORECASE,
)

# First words that are not imperative: "adds", "added", "adding" for "add"
THIRD_PERSON = re.compile(
    r"""
    ^(adds|allows|builds|changes|checks|creates|deletes|drops|ensures|fixes
      |gets|handles|improves|keeps|makes|moves|prevents|raises|reads|removes
      |renames|replaces|returns|runs|sets|skips|stops|supports|switches
      |updates|uses|writes)$
    """,
    re.VERBOSE,
)
NOT_PAST = ("embed", "exceed", "feed", "need", "proceed", "seed", "shed", "speed")
NOT_GERUND = ("bring", "ping", "ring", "string")

# Words that fill a body without saying anything. Reported, not refused.
FILLER = re.compile(
    r"""
    \b(this\ (commit|change|pr|patch)|comprehensive|robust|seamless(ly)?
       |leverag(e|es|ing)|utiliz(e|es|ing)|streamlin(e|es|ed|ing)
       |enhanc(e|es|ed|ing|ement)|in\ order\ to|ensur(e|es|ing)\ that
       |it\ is\ worth\ noting|furthermore|additionally)\b
    """,
    re.VERBOSE | re.IGNORECASE,
)


def allowed_scopes():
    """Return the scopes in commit_scopes.txt, or None when there is no file."""
    path = Path(__file__).with_name("commit_scopes.txt")
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and line[0] != "#"]


def message_lines(message):
    """Return the lines git keeps: no comments and no diff from commit -v."""
    lines = []
    for line in message.splitlines():
        if line.startswith("# ------------------------ >8"):
            break
        if not line.startswith("#"):
            lines.append(line.rstrip())
    while lines and not lines[-1]:
        lines.pop()
    return lines


def is_exempt(summary):
    """Return True for a message written by git or by CI."""
    return summary.startswith(EXEMPT_PREFIXES) or "[skip ci]" in summary


def subject_problems(subject):
    """Return what is wrong with the words after the type and the colon."""
    found = []
    first = subject.split()[0]
    word = first.lower()
    if first[0].isupper() and not first.isupper():
        found.append("the subject starts with a capital letter")
    if VAGUE.match(subject):
        found.append("the subject does not say what changed")
    elif THIRD_PERSON.match(word):
        found.append(f"write `{word}` as an imperative, not in the third person")
    elif word.endswith("ed") and len(word) > 4 and word not in NOT_PAST:
        found.append(f"write `{word}` as an imperative, not in the past tense")
    elif word.endswith("ing") and len(word) > 5 and word not in NOT_GERUND:
        found.append(f"write `{word}` as an imperative, not as `-ing`")
    return found


def summary_problems(summary, scopes):
    """Return what is wrong with the first line."""
    found = []
    match = SUMMARY.match(summary)
    if not match:
        found.append("the summary must read `type(scope)!: subject`")
    else:
        kind, scope = match["type"], match["scope"]
        if kind not in TYPES:
            found.append(f"`{kind}` is not a type; use one of {', '.join(TYPES)}")
        if scope is not None and scopes is not None and scope not in scopes:
            found.append(f"`{scope}` is not a scope; use one of {', '.join(scopes)}")
        found.extend(subject_problems(match["subject"]))
    if len(summary) > MAX_SUMMARY_LENGTH:
        size = len(summary)
        found.append(f"the summary is {size} characters; the limit is 72")
    if summary.endswith("."):
        found.append("the summary ends with a period")
    return found


def is_long(line):
    """Return True for a body line that should have been wrapped."""
    if len(line) <= MAX_BODY_LINE_LENGTH:
        return False
    # A URL, a quoted command or a table cannot be wrapped
    return " " in line.strip() and "://" not in line and line[0] not in " \t|>"


def problems(message, scopes=None):
    """Return what is wrong with a commit message, or an empty list."""
    lines = message_lines(message)
    if not lines:
        return ["the message is empty"]
    summary = lines[0]
    if is_exempt(summary):
        return []

    found = summary_problems(summary, scopes)
    if len(lines) > 1 and lines[1]:
        found.append("the second line must be blank")

    body = [line for line in lines[2:] if line and not TRAILER.match(line)]
    if not body:
        found.append("there is no body; say what changed and why")
    long_lines = sum(1 for line in lines[2:] if is_long(line))
    if long_lines:
        found.append(f"{long_lines} body line(s) are longer than 72 characters")

    match = SUMMARY.match(summary)
    marked = bool(match and match["breaking"])
    explained = any(BREAKING.match(line) for line in lines[2:])
    if marked and not explained:
        found.append("`!` needs a `Breaking:` paragraph in the body")
    if explained and not marked:
        found.append("a `Breaking:` paragraph needs `!` before the colon")

    if CREDIT.search("\n".join(lines)):
        found.append("the message credits a co-author or a tool; remove it")
    return found


def warnings(message):
    """Return what is worth a second look but does not block the commit."""
    lines = message_lines(message)
    if not lines or is_exempt(lines[0]):
        return []
    found = []
    if " and " in lines[0]:
        found.append('the summary has "and"; is this two commits?')
    filler = sorted({m.group(0).lower() for m in FILLER.finditer("\n".join(lines))})
    if filler:
        found.append(f"filler in the message: {', '.join(filler)}")
    return found


def messages_in(rev_range):
    """Return the message of every commit a person made in the range."""
    fmt = "--format=%h%x1f%an%x1f%B%x1e"
    command = ["git", "log", "--no-merges", fmt, rev_range]
    log = subprocess.run(command, capture_output=True, text=True, check=True)
    messages = {}
    for record in log.stdout.split("\x1e"):
        if not record.strip():
            continue
        commit, author, message = record.strip("\n").split("\x1f", 2)
        # dependabot and github-actions write their own format
        if not author.endswith("[bot]"):
            messages[commit] = message
    return messages


def main(argv):
    """Check one message file, or every commit in a range."""
    if len(argv) == 2 and argv[0] == "--range":
        messages = messages_in(argv[1])
    elif len(argv) == 1:
        text = Path(argv[0]).read_text(encoding="utf-8")
        messages = {"commit message": text}
    else:
        print("usage: check_commit_message.py <file> | --range <range>")
        return 2

    scopes = allowed_scopes()
    failed = False
    for name, message in messages.items():
        for problem in problems(message, scopes):
            failed = True
            print(f"{name}: {problem}", file=sys.stderr)
        for warning in warnings(message):
            print(f"{name}: warning: {warning}", file=sys.stderr)
    if failed:
        print('See "Commit format" in CONTRIBUTING.md.', file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
