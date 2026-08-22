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
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOTS = [
    ROOT / "packages/webcompy/src/webcompy",
    ROOT / "packages/webcompy-server/src/webcompy_server",
    ROOT / "packages/webcompy-cli/src/webcompy_cli",
    ROOT / "packages/webcompy-testing/src/webcompy_testing",
]
DEFAULT_BASELINE = ROOT / "scripts" / "check-docstrings-baseline.txt"

IMPORTANT_INTERNALS = [
    "webcompy.components._generator:ComponentStore",
    "webcompy.elements.types._element:ElementBase",
    "webcompy.signal._graph:SignalNode",
]

FORBIDDEN_RES = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (r"openspec", r"spec\.md", r"tasks\.md", r"proposal\.md", r"design\.md")
]

Gap = tuple[Path, int, str]


def _docstring(node: ast.AST) -> ast.Expr | None:
    body = getattr(node, "body", None)
    if not body:
        return None
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
        and first.value.value.strip()
    ):
        return first
    return None


def _decorator_leaf_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_leaf_name(node.func)
    return None


def _is_exempt_method(node: ast.AST) -> bool:
    for decorator in getattr(node, "decorator_list", []):
        leaf = _decorator_leaf_name(decorator)
        if leaf in ("overload", "setter", "deleter"):
            return True
    return False


def _assigned_name(node: ast.AST) -> str:
    if isinstance(node, ast.Assign):
        return cast("ast.Name", node.targets[0]).id
    return cast("ast.Name", node.target).id


def _assignment_target(stmt: ast.stmt, name: str) -> str | None:
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        return stmt.targets[0].id if stmt.targets[0].id == name else None
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return stmt.target.id if stmt.target.id == name else None
    return None


def _is_type_checking_test(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "TYPE_CHECKING"
    if isinstance(node, ast.Attribute):
        return node.attr == "TYPE_CHECKING"
    return False


def _top_level_statements(tree: ast.Module) -> list[ast.stmt]:
    statements = list(tree.body)
    for stmt in tree.body:
        if isinstance(stmt, ast.If) and _is_type_checking_test(stmt.test):
            statements.extend(stmt.body)
    return statements


def _import_target(importer: str, importer_is_package: bool, node: ast.ImportFrom) -> str | None:
    if node.module is None:
        return None
    if node.level == 0:
        return node.module
    package = importer if importer_is_package else ".".join(importer.split(".")[:-1])
    parts = package.split(".")
    cut = node.level - 1
    if cut > len(parts):
        return None
    base = parts[: len(parts) - cut] if cut else parts
    return ".".join([*base, node.module])


def _display_path(path: Path, roots: list[Path]) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        pass
    for root in roots:
        try:
            return str(path.relative_to(root))
        except ValueError:
            pass
    return str(path)


class _SourceIndex:
    def __init__(self) -> None:
        self.sources: dict[Path, str] = {}
        self.trees: dict[Path, ast.Module] = {}

    def source(self, path: Path) -> str:
        if path not in self.sources:
            with tokenize.open(path) as handle:
                self.sources[path] = handle.read()
        return self.sources[path]

    def tree(self, path: Path) -> ast.Module:
        if path not in self.trees:
            self.trees[path] = ast.parse(self.source(path), filename=str(path))
        return self.trees[path]


class _Registry:
    def __init__(self, roots: list[Path], index: _SourceIndex) -> None:
        self.roots = roots
        self.index = index
        self._module_of: dict[Path, str] = {}

    def py_files(self) -> list[tuple[Path, str]]:
        files: list[tuple[Path, str]] = []
        for root in self.roots:
            for path in sorted(root.rglob("*.py")):
                if path.name.endswith(".pyi"):
                    continue
                relative = path.relative_to(root)
                parts = list(relative.with_suffix("").parts)
                if parts[-1] == "__init__":
                    parts.pop()
                module = ".".join([root.name, *parts])
                self._module_of[path] = module
                files.append((path, module))
        files.sort(key=lambda pair: str(pair[0]))
        return files

    def locate(self, module: str) -> Path | None:
        parts = module.split(".")
        for root in self.roots:
            if root.name != parts[0]:
                continue
            if len(parts) == 1:
                package_init = root / "__init__.py"
                return package_init if package_init.exists() else None
            sub = root.joinpath(*parts[1:])
            package_init = sub / "__init__.py"
            if package_init.exists():
                return package_init
            module_file = sub.with_suffix(".py")
            if module_file.exists():
                return module_file
        return None

    def module_of(self, path: Path) -> str:
        return self._module_of[path]


class _Checker:
    def __init__(self, registry: _Registry, index: _SourceIndex, roots: list[Path]) -> None:
        self.registry = registry
        self.index = index
        self.roots = roots
        self.gaps: dict[str, Gap] = {}

    def add_gap(self, path: Path, lineno: int, key: str) -> None:
        self.gaps.setdefault(key, (path, lineno, key))

    def resolve(self, module: str, name: str, visited: frozenset[tuple[str, str]]) -> tuple[Path, str, ast.AST] | None:
        marker = (module, name)
        if marker in visited:
            return None
        visited = visited | {marker}
        path = self.registry.locate(module)
        if path is None:
            return None
        tree = self.index.tree(path)
        winner: tuple[str, ast.AST | str, str | None] | None = None
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and stmt.name == name:
                winner = ("definition", stmt, None)
            elif isinstance(stmt, ast.ImportFrom):
                for alias in stmt.names:
                    if (alias.asname or alias.name) == name:
                        winner = ("importfrom", stmt, alias.name)
                        break
            elif isinstance(stmt, (ast.Assign, ast.AnnAssign)) and _assignment_target(stmt, name) == name:
                if isinstance(stmt.value, ast.Name):
                    winner = ("alias", stmt.value.id, None)
                else:
                    winner = ("definition", stmt, None)
        if winner is None:
            for stmt in tree.body:
                if isinstance(stmt, ast.If) and _is_type_checking_test(stmt.test):
                    for inner in stmt.body:
                        if isinstance(inner, ast.ImportFrom):
                            for alias in inner.names:
                                if (alias.asname or alias.name) == name:
                                    winner = ("importfrom", inner, alias.name)
        if winner is None:
            return None
        kind, payload, import_name = winner
        if kind == "alias":
            return self.resolve(module, cast("str", payload), visited)
        if kind == "importfrom":
            node = cast("ast.ImportFrom", payload)
            target = _import_target(module, path.name == "__init__.py", node)
            if target is None:
                return None
            return self.resolve(target, cast("str", import_name), visited)
        return (path, module, cast("ast.AST", payload))

    def check_definition(self, path: Path, module: str, node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _docstring(node) is None:
                self.add_gap(path, node.lineno, f"{module}:{node.name}")
        elif isinstance(node, ast.ClassDef):
            self.check_class(path, module, node.name, node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and not self._has_trailing_docstring(path, node):
            self.add_gap(path, node.lineno, f"{module}:{_assigned_name(node)}")

    def _has_trailing_docstring(self, path: Path, node: ast.AST) -> bool:
        body = self.index.tree(path).body
        position = body.index(cast("ast.stmt", node))
        following = body[position + 1] if position + 1 < len(body) else None
        return (
            following is not None
            and isinstance(following, ast.Expr)
            and isinstance(following.value, ast.Constant)
            and isinstance(following.value.value, str)
        )

    def check_class(self, path: Path, module: str, qualname: str, node: ast.ClassDef) -> None:
        if _docstring(node) is None:
            self.add_gap(path, node.lineno, f"{module}:{qualname}")
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if "." in child.name or child.name.startswith("_"):
                    continue
                if _is_exempt_method(child):
                    continue
                if _docstring(child) is None:
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
            if _docstring(self.index.tree(path)) is None:
                self.add_gap(path, 1, module)
            if path.name == "__init__.py":
                self.collect_re_exports(path, module)
        for entry in IMPORTANT_INTERNALS:
            module, _, name = entry.partition(":")
            resolved = self.resolve(module, name, frozenset())
            if resolved is not None:
                self.check_definition(*resolved)

    def collect_re_exports(self, path: Path, module: str) -> None:
        tree = self.index.tree(path)
        for stmt in _top_level_statements(tree):
            if not isinstance(stmt, ast.ImportFrom) or stmt.module is None:
                continue
            target = _import_target(module, True, stmt)
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

    def forbidden_references(self) -> list[tuple[Path, int]]:
        violations: list[tuple[Path, int]] = []
        for path, _module in self.registry.py_files():
            source = self.index.source(path)
            tree = self.index.tree(path)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    docstring = _docstring(node)
                    if docstring is not None and any(
                        pattern.search(docstring.value.value) for pattern in FORBIDDEN_RES
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
