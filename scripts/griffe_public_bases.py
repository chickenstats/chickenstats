"""Griffe extension that turns the base classes of inspected classes into cross-references.

The docs build inspects the package at runtime, because ``@shared_doc`` sets docstrings when the module is
imported. Inspection records each base class as a plain string, which the docs render without a link, so
this extension replaces each string with a name that the docs can link to the base's own page.

A base is named by the shortest import path that reaches it: ``Exception`` rather than
``builtins.Exception``, and ``requests.Session`` rather than ``requests.sessions.Session``, which is the
name the requests inventory uses.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from griffe import Extension, ExprName

if TYPE_CHECKING:
    import ast

    from griffe import Class, Expr, Inspector, ObjectNode, Visitor


def _public_path(base: type) -> str:
    """Return the shortest import path for ``base``: its top-level package when that re-exports it."""
    if base.__module__ == "builtins":
        return base.__qualname__

    top_level = base.__module__.split(".")[0]

    try:
        if getattr(importlib.import_module(top_level), base.__qualname__, None) is base:
            return f"{top_level}.{base.__qualname__}"
    except ImportError:
        pass

    return f"{base.__module__}.{base.__qualname__}"


class PublicBases(Extension):
    """Replace the string bases of inspected classes with names the docs can cross-reference."""

    def on_class_instance(
        self, *, node: ast.AST | ObjectNode, cls: Class, agent: Visitor | Inspector, **kwargs: Any
    ) -> None:
        """Rewrite the bases of a class that was just inspected."""
        obj = getattr(node, "obj", None)

        if not isinstance(obj, type):
            return

        bases = [base for base in obj.__bases__ if base is not object]

        # Inspection keeps the same order, so the names line up with the strings they replace
        if len(bases) != len(cls.bases) or not all(isinstance(base, str) for base in cls.bases):
            return

        names: list[Expr | str] = []

        for base in bases:
            module, _, name = _public_path(base).rpartition(".")
            names.append(ExprName(name, parent=module or None))

        cls.bases = names
