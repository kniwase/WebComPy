#!/usr/bin/env python3
"""Check that browser test modules stay CPython-importable at module level.

The browser test tier (``tests/browser/**``) is collected by standard pytest
import on CPython and later re-imported inside the harness PyScript page.
Browser-only modules (``js``, ``pyscript``, ``pyodide``) and testing fakes
must therefore be imported inside functions or hook bodies, never at module
top level. This checker enforces that invariant with a helpful message.

Usage:
    python3 scripts/check-browser-imports.py [ROOT]

``ROOT`` defaults to the repository's ``tests/browser`` directory. Exits 1 on
any violation.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

BROWSER_ONLY_MODULES = frozenset({"js", "pyscript", "pyodide"})
FORBIDDEN_FAKE_PREFIXES = ("Fake", "_")
FAKE_SOURCE_MODULES = frozenset({"webcompy_testing"})

VIOLATION_MESSAGE = (
    "{path}:{lineno}: top-level import of '{module}' is not allowed in "
    "tests/browser. Browser-only and fake-port imports must be function-local "
    "so the module stays CPython-importable (see the CPython-importability "
    "invariant of the browser test harness)."
)


def _check_import(tree: ast.Module, path: Path) -> list[str]:
    problems: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in BROWSER_ONLY_MODULES:
                    problems.append(VIOLATION_MESSAGE.format(path=path, lineno=node.lineno, module=alias.name))
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if node.level == 0 and root in BROWSER_ONLY_MODULES:
                problems.append(VIOLATION_MESSAGE.format(path=path, lineno=node.lineno, module=node.module or ""))
            if node.level == 0 and root in FAKE_SOURCE_MODULES:
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_FAKE_PREFIXES) and alias.name != "__all__":
                        problems.append(
                            VIOLATION_MESSAGE.format(
                                path=path, lineno=node.lineno, module=f"{node.module}.{alias.name}"
                            )
                        )
    return problems


def check_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return _check_import(tree, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parent.parent / "tests" / "browser"
    parser.add_argument("root", nargs="?", default=default_root, type=Path)
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"browser-test import checker: missing directory {args.root}")
        return 1

    problems: list[str] = []
    for path in sorted(args.root.rglob("*.py")):
        problems.extend(check_file(path))

    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print(f"\n{len(problems)} violation(s) found.", file=sys.stderr)
        return 1
    print(f"OK: {args.root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
