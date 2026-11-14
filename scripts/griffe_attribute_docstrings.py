"""Griffe extension that gives inspected module constants the docstrings written under them.

The docs build inspects the package at runtime, and inspection gives a constant the docstring of its
value's type, so a tuple constant shows Python's description of ``tuple``. This extension reads the
string literal written under the assignment in the source and uses that instead.
"""

from __future__ import annotations

import ast
import inspect
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from griffe import Docstring, Extension

if TYPE_CHECKING:
    from griffe import Attribute, Inspector, ObjectNode, Visitor


@cache
def _source_docstrings(path: str) -> dict[str, str]:
    """Return the docstring under each module-level assignment in the file at ``path``."""
    with open(path, encoding="utf-8") as source:
        body = ast.parse(source.read()).body

    docstrings = {}

    for statement, following in zip(body, body[1:], strict=False):
        if isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
        elif isinstance(statement, ast.Assign):
            targets = statement.targets
        else:
            continue

        if not (
            isinstance(following, ast.Expr)
            and isinstance(following.value, ast.Constant)
            and isinstance(following.value.value, str)
        ):
            continue

        for target in targets:
            if isinstance(target, ast.Name):
                docstrings[target.id] = inspect.cleandoc(following.value.value)

    return docstrings


class AttributeDocstrings(Extension):
    """Replace a module constant's type docstring with the one written under it in the source."""

    def on_attribute_instance(
        self, *, node: ast.AST | ObjectNode, attr: Attribute, agent: Visitor | Inspector, **kwargs: Any
    ) -> None:
        """Swap the docstring of a module attribute that was just inspected."""
        module = attr.parent

        # A namespace package has a list of paths and no source of its own.
        if module is None or not module.is_module or not isinstance(module.filepath, Path):
            return

        docstring = _source_docstrings(str(module.filepath)).get(attr.name)

        if docstring is not None:
            attr.docstring = Docstring(docstring, parent=attr)
