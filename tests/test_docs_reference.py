"""Every public name in chicken_nhl, rapm and viz has an entry in the docs reference.

A name is documented when a ``:::`` directive in docs/reference names it, lists it under
``members:``, or documents the whole module it is defined in. The source is read with ``ast``
rather than imported, so the check needs neither the docs build nor the ``plotting`` and
``rapm`` extras.
"""

import ast
import re
from pathlib import Path

import pytest

import chickenstats

ROOT = Path(__file__).resolve().parents[1]
# The installed package, not ROOT / "src", so the check also runs against a wheel with src/ removed
SRC = Path(chickenstats.__file__).resolve().parents[1]
REFERENCE = ROOT / "docs" / "reference"

DIRECTIVE = re.compile(r"^#*:::\s*(?P<ident>[\w.]+)\s*$")
MEMBER = re.compile(r"^-\s*(?P<name>\w+)\s*$")


def module_file(path: str) -> Path | None:
    """Return the source file of the module at the dotted ``path``, or None when it is not a module."""
    base = SRC.joinpath(*path.split("."))
    for candidate in (base / "__init__.py", base.with_suffix(".py")):
        if candidate.is_file():
            return candidate
    return None


def read_module(path: str) -> ast.Module:
    """Parse the source of the module at the dotted ``path``."""
    file = module_file(path)
    assert file is not None, f"{path} is not a chickenstats module"
    return ast.parse(file.read_text())


def public_names(path: str) -> list[str]:
    """Return the module's ``__all__``, or the names it defines without a leading underscore."""
    defined = []
    for node in read_module(path).body:
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "__all__" in targets:
                return list(ast.literal_eval(node.value))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            targets = [node.name]
        else:
            continue
        defined.extend(name for name in targets if not name.startswith("_"))
    return defined


def import_sources(path: str) -> dict[str, str]:
    """Map each name the module imports to the dotted path it is imported from."""
    return {
        alias.asname or alias.name: f"{node.module}.{alias.name}"
        for node in read_module(path).body
        if isinstance(node, ast.ImportFrom) and node.module
        for alias in node.names
    }


def listed_members(options: list[str]) -> list[str] | None:
    """Return the names under a directive's ``members:`` option, or None when it has none."""
    members = None
    for line in options:
        stripped = line.strip()
        if stripped == "members:":
            members = []
        elif members is not None and (member := MEMBER.match(stripped)):
            members.append(member["name"])
        elif members:
            break
    return members


def documented_paths() -> set[str]:
    """Return every dotted path the reference pages document, members included."""
    documented = set()
    for page in REFERENCE.rglob("*.md"):
        lines = page.read_text().splitlines()
        for number, line in enumerate(lines):
            if not (match := DIRECTIVE.match(line)):
                continue
            ident = match["ident"]
            documented.add(ident)

            # The directive's options are the indented lines that follow it
            options = []
            for option in lines[number + 1 :]:
                if option.strip() and not option.startswith(" "):
                    break
                options.append(option)

            members = listed_members(options)
            if members is None and module_file(ident) is not None:
                # A directive without a members list documents every public name of a module
                members = public_names(ident)
            documented.update(f"{ident}.{name}" for name in members or [])
    return documented


def expected_names() -> list[tuple[str, set[str]]]:
    """Return each public name with the dotted paths a directive can use for it."""
    expected = []
    for module in ("chickenstats.chicken_nhl", "chickenstats.chicken_nhl.viz"):
        sources = import_sources(module)
        for name in public_names(module):
            expected.append((f"{module}.{name}", {f"{module}.{name}", sources.get(name, "")}))

    rapm = "chickenstats.chicken_nhl.rapm"
    expected.extend((f"{rapm}.{name}", {f"{rapm}.{name}"}) for name in public_names(rapm))

    identity = "chickenstats.chicken_nhl.identity.identity_columns"
    expected.append((identity, {identity}))
    return expected


DOCUMENTED = documented_paths()


@pytest.mark.parametrize(("name", "paths"), expected_names(), ids=lambda value: value if isinstance(value, str) else "")
def test_public_name_in_reference(name, paths):
    assert paths & DOCUMENTED, f"{name} has no entry in docs/reference; add it to a ::: directive"


def test_directive_options_are_read():
    # Guards the parser: a page that lists members must not count as documenting the whole class
    assert "chickenstats.chicken_nhl.season.Season.schedule" in DOCUMENTED
    assert "chickenstats.chicken_nhl.season.Season.multi_season_schedule" not in DOCUMENTED
    assert "chickenstats.chicken_nhl.contract.assert_chronological" in DOCUMENTED
