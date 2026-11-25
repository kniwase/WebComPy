#!/usr/bin/env python3
"""Check docstring coverage of the public WebComPy API surface.

The public surface is the set of names re-exported through any package or
subpackage ``__init__.py`` of the four packages under ``packages/*/src``,
resolved through import chains (including ``as`` aliases) to the definition
site. Requirements enforced:

1. Every ``*.py`` module has a module docstring.
2. Every re-exported public function, class, public method, property getter,
   and public nested class has a docstring.
3. Public constants re-exported through the public surface (plus entries of
   ``IMPORTANT_INTERNALS``) carry a PEP 224 attribute docstring.
4. Docstrings and comments do not reference OpenSpec artifacts.

The mechanical forbidden-reference scan is deliberately narrow (the five patterns
in ``FORBIDDEN_RES``: the ``openspec`` path and the four artifact file names).
Policing of change/spec names, requirement/scenario IDs, and task numbers is
owned by AI code review as a mandatory perspective, not by this script.

Gaps are tracked in a baseline file that ratchets downward: an undocumented
symbol absent from the baseline fails, and a baseline entry whose symbol now
has a docstring fails, forcing monotonic shrinkage. A missing baseline file
means strict mode (zero tolerance).

Usage:
    python3 scripts/check-docstrings.py
    python3 scripts/check-docstrings.py --write-baseline
    python3 scripts/check-docstrings.py --list-missing [PREFIX]
    python3 scripts/check-docstrings.py --root PATH --baseline PATH
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import tokenize
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _api_surface import (  # noqa: E402
    IMPORTANT_INTERNALS,
    PACKAGE_ROOTS,
    ROOT,
    Gap,
    Registry,
    SourceIndex,
    assigned_name,
    assignment_target,
    display_path,
    docstring_expr,
    import_target,
    is_exempt_method,
    resolve_symbol,
    top_level_statements,
    trailing_docstring_expr,
)

DEFAULT_BASELINE = ROOT / "scripts" / "check-docstrings-baseline.txt"

FORBIDDEN_RES = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (r"openspec", r"spec\.md", r"tasks\.md", r"proposal\.md", r"design\.md")
]

_SourceIndex = SourceIndex
_Registry = Registry
_docstring = docstring_expr
_assigned_name = assigned_name
_assignment_target = assignment_target
_import_target = import_target
_is_exempt_method = is_exempt_method
_top_level_statements = top_level_statements
_display_path = display_path


class _Checker:
    def __init__(self, registry: Registry, index: SourceIndex, roots: list[Path]) -> None:
        self.registry = registry
        self.index = index
        self.roots = roots
        self.gaps: dict[str, Gap] = {}

    def add_gap(self, path: Path, lineno: int, key: str) -> None:
        self.gaps.setdefault(key, (path, lineno, key))

    def resolve(self, module: str, name: str, visited: frozenset[tuple[str, str]]) -> tuple[Path, str, ast.AST] | None:
        return resolve_symbol(self.registry, self.index, module, name, visited)

    def check_definition(self, path: Path, module: str, node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if docstring_expr(node) is None:
                self.add_gap(path, node.lineno, f"{module}:{node.name}")
        elif isinstance(node, ast.ClassDef):
            self.check_class(path, module, node.name, node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and not self._has_trailing_docstring(path, node):
            self.add_gap(path, node.lineno, f"{module}:{assigned_name(node)}")

    def _has_trailing_docstring(self, path: Path, node: ast.AST) -> bool:
        return trailing_docstring_expr(self.index.tree(path).body, node) is not None

    def check_class(self, path: Path, module: str, qualname: str, node: ast.ClassDef) -> None:
        if docstring_expr(node) is None:
            self.add_gap(path, node.lineno, f"{module}:{qualname}")
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if "." in child.name or child.name.startswith("_"):
                    continue
                if is_exempt_method(child):
                    continue
                if docstring_expr(child) is None:
                    self.add_gap(path, child.lineno, f"{module}:{qualname}.{child.name}")
            elif isinstance(child, ast.ClassDef):
                if child.name.startswith("_"):
                    continue
                self.check_class(path, module, f"{qualname}.{child.name}", child)

    def collect(self) -> None:
        for path, module in self.registry.py_files():
            source = self.index.source(path)
            if not source.strip():
                continue
            if docstring_expr(self.index.tree(path)) is None:
                self.add_gap(path, 1, module)
            if path.name == "__init__.py":
                self.collect_re_exports(path, module)
                self.collect_init_definitions(path, module)
        for entry in IMPORTANT_INTERNALS:
            module, _, name = entry.partition(":")
            resolved = self.resolve(module, name, frozenset())
            if resolved is not None:
                self.check_definition(*resolved)

    def collect_re_exports(self, path: Path, module: str) -> None:
        tree = self.index.tree(path)
        for stmt in top_level_statements(tree):
            if not isinstance(stmt, ast.ImportFrom) or stmt.module is None:
                continue
            target = import_target(module, True, stmt)
            if target is None:
                continue
            for alias in stmt.names:
                if alias.name == "*" or alias.name.startswith("_"):
                    continue
                if (alias.asname or alias.name).startswith("_"):
                    continue
                resolved = self.resolve(target, alias.name, frozenset())
                if resolved is not None:
                    self.check_definition(*resolved)

    def collect_init_definitions(self, path: Path, module: str) -> None:
        """Require docstrings on public functions and classes defined in ``__init__.py``.

        Names defined directly inside a package ``__init__.py`` are part of
        the public surface even though they are not re-exported through an
        ``ImportFrom``, so the re-export walk alone cannot see them.
        Overload stubs follow the same exemption as class methods: the
        docstring lives on the implementation.
        """
        tree = self.index.tree(path)
        for stmt in top_level_statements(tree):
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_exempt_method(stmt):
                continue
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not stmt.name.startswith(
                "_"
            ):
                self.check_definition(path, module, stmt)

    def forbidden_references(self) -> list[tuple[Path, int]]:
        violations: list[tuple[Path, int]] = []
        for path, _module in self.registry.py_files():
            source = self.index.source(path)
            tree = self.index.tree(path)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    docstring = docstring_expr(node)
                    if (
                        docstring is not None
                        and isinstance(docstring.value, ast.Constant)
                        and isinstance(docstring.value.value, str)
                        and any(pattern.search(docstring.value.value) for pattern in FORBIDDEN_RES)
                    ):
                        violations.append((path, docstring.lineno))
            for token in tokenize.generate_tokens(iter(source.splitlines(keepends=True)).__next__):
                if token.type == tokenize.COMMENT and any(pattern.search(token.string) for pattern in FORBIDDEN_RES):
                    violations.append((path, token.start[0]))
        violations.sort(key=str)
        return violations


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check-docstrings", description="Check docstring coverage of the public WebComPy API surface."
    )
    parser.add_argument("--root", metavar="PATH", help="scan this package root instead of the four default roots")
    parser.add_argument("--baseline", metavar="PATH", help="use this baseline file instead of the default")
    parser.add_argument("--write-baseline", action="store_true", help="rewrite the baseline from current gaps")
    parser.add_argument("--list-missing", action="store_true", help="print current gaps, ignoring the baseline")
    parser.add_argument("prefix", nargs="?", default="", help="dotted module path prefix filter for --list-missing")
    return parser


def load_baseline(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    roots = [Path(args.root).resolve()] if args.root else PACKAGE_ROOTS
    for root in roots:
        if not root.is_dir():
            print(f"error: package root not found: {root}", file=sys.stderr)
            return 1
    baseline_path = Path(args.baseline).resolve() if args.baseline else DEFAULT_BASELINE

    index = _SourceIndex()
    registry = _Registry(roots, index)
    checker = _Checker(registry, index, roots)
    checker.collect()
    gap_keys = sorted(checker.gaps)

    if args.write_baseline:
        header = "# Documentation gaps (regenerate with scripts/check-docstrings.py --write-baseline)"
        baseline_path.write_text("\n".join([header, *gap_keys, ""]), encoding="utf-8")
        print(f"wrote {len(gap_keys)} baseline entries to {baseline_path}")
        return 0

    if args.list_missing:
        for key in gap_keys:
            if not args.prefix or key.startswith(args.prefix):
                print(key)
        return 0

    baseline = load_baseline(baseline_path)
    errors: list[str] = []
    if baseline is None:
        for path, lineno, key in checker.gaps.values():
            errors.append(f"{_display_path(path, roots)}:{lineno}: {key} (missing docstring)")
    else:
        for key in gap_keys:
            path, lineno, _ = checker.gaps[key]
            if key not in baseline:
                errors.append(f"{_display_path(path, roots)}:{lineno}: {key} (missing docstring)")
        for key in sorted(baseline):
            if key not in checker.gaps:
                path = registry.locate(key.split(":", 1)[0])
                location = _display_path(path, roots) if path is not None else key
                errors.append(f"{location}:1: {key} (docstring now present; remove from baseline)")
    for path, lineno in checker.forbidden_references():
        errors.append(f"{_display_path(path, roots)}:{lineno}: forbidden OpenSpec reference")

    if errors:
        for error in sorted(errors):
            print(f"error: {error}", file=sys.stderr)
        print(f"{len(errors)} violation(s) found", file=sys.stderr)
        return 1

    print("OK: no undocumented public interfaces and no forbidden OpenSpec references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
