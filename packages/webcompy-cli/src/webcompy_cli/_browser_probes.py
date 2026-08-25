"""AST classifier partitioning ``tests/`` modules for PyScript dual-run eligibility.

The classifier walks test modules without importing them, parses each file's
AST, and tags a module as dual-run eligible only when its top level is safe to
execute inside a real PyScript interpreter: browser-only imports (``js``,
``pyscript``, ``pyodide``), ``e2e.*`` imports, and fake-port symbols from
``webcompy_testing`` are disqualifying, and any module-scope side-effecting
call (except the registration-style ``pytest.mark.*`` / ``pytest.fixture``
call chains) is disqualifying. Imports of ``js``-family symbols inside
function bodies do not disqualify a module because those imports are only
evaluated in-page.

A trailing pragma comment on its own line overrides the AST judgment:

- ``# browser-dualrun: eligible`` forces an otherwise ineligible module into
  the eligible set.
- ``# browser-dualrun: skip`` forces an otherwise eligible module out of the
  eligible set.

This module intentionally duplicates ``BROWSER_TEST_DIR`` instead of importing
it from the harness server module so that classification stays importable in
lightweight lint contexts (no Starlette/uvicorn dependency).
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

BROWSER_TEST_DIR = "tests/browser"
DUALRUN_BASELINE_DIR = "tests/.dualrun"
PRAGMA_ELIGIBLE = "browser-dualrun: eligible"
PRAGMA_SKIP = "browser-dualrun: skip"

_BROWSER_ONLY_MODULES = frozenset({"js", "pyscript", "pyodide"})
_FAKE_SOURCE_MODULE = "webcompy_testing"
_FAKE_SYMBOL_PREFIXES = ("Fake", "_")
_E2E_PACKAGE_ROOT = "e2e"


@dataclass
class DualRunClassification:
    """Result of partitioning ``tests/`` modules for dual-run execution.

    Attributes:
        eligible: Repo-relative POSIX paths of dual-run-eligible modules,
            sorted ascending.
        ineligible: Mapping of repo-relative POSIX path to the reason the
            module was excluded, sorted by path.

    """

    eligible: list[str] = field(default_factory=list)
    ineligible: dict[str, str] = field(default_factory=dict)


def _pragma_of(source: str) -> str | None:
    """Return the override pragma found in the source, if any.

    Args:
        source: Full text of the module under classification.

    Returns:
        ``PRAGMA_ELIGIBLE`` or ``PRAGMA_SKIP`` when a matching standalone
        comment line exists, otherwise ``None``.

    """
    for line in source.splitlines():
        stripped = line.strip()
        if stripped == f"# {PRAGMA_ELIGIBLE}":
            return PRAGMA_ELIGIBLE
        if stripped == f"# {PRAGMA_SKIP}":
            return PRAGMA_SKIP
    return None


def _call_root_path(call: ast.Call) -> list[str]:
    """Resolve the dotted attribute chain rooted at a plain name for a call.

    Args:
        call: The ``ast.Call`` node to resolve.

    Returns:
        The name/attribute segments from the root name outward (for example
        ``["pytest", "mark", "parametrize"]``), or an empty list when the call
        target is not rooted at a plain name.

    """
    parts: list[str] = []
    node: ast.AST = call.func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return []
    parts.append(node.id)
    parts.reverse()
    return parts


def _is_allowed_call(call: ast.Call) -> bool:
    """Whether a module-scope call is a harmless pytest registration call.

    Args:
        call: The ``ast.Call`` node to inspect.

    Returns:
        True for calls whose target resolves through ``pytest.mark.*`` or
        ``pytest.fixture``; these only attach metadata and have no runtime
        side effects on either interpreter.

    """
    parts = _call_root_path(call)
    return len(parts) >= 2 and parts[0] == "pytest" and parts[1] in ("mark", "fixture")


def _reason_for_statement(stmt: ast.stmt) -> str | None:
    """Inspect one top-level statement for disqualifying content.

    Function, async function, and class bodies are not descended into because
    their internals only execute when invoked; their decorators are inspected
    individually. All other statements are walked fully so nested calls (for
    example the right-hand side of an assignment) are caught.

    Args:
        stmt: A top-level AST statement.

    Returns:
        A human-readable reason string when the statement disqualifies the
        module, otherwise ``None``.

    """
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        for decorator in stmt.decorator_list:
            for node in ast.walk(decorator):
                if isinstance(node, ast.Call) and not _is_allowed_call(node):
                    return f"module-scope side-effecting call at line {node.lineno}"
        return None
    for node in ast.walk(stmt):
        if isinstance(node, ast.Call) and not _is_allowed_call(node):
            return f"module-scope side-effecting call at line {node.lineno}"
    return None


def _reason_for_imports(tree: ast.Module) -> str | None:
    """Scan top-level imports for browser-only, e2e, or fake-port symbols.

    Args:
        tree: Parsed module AST.

    Returns:
        A human-readable reason string naming the disqualifying import, or
        ``None`` when all top-level imports are acceptable.

    """
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                root = alias.name.split(".")[0]
                if root in _BROWSER_ONLY_MODULES or root == _E2E_PACKAGE_ROOT:
                    return f"top-level import of '{alias.name}' at line {stmt.lineno}"
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.level != 0:
                continue
            module = stmt.module or ""
            root = module.split(".")[0]
            if root in _BROWSER_ONLY_MODULES or root == _E2E_PACKAGE_ROOT:
                return f"top-level import from '{module}' at line {stmt.lineno}"
            if root == _FAKE_SOURCE_MODULE:
                for alias in stmt.names:
                    if alias.name != "__all__" and alias.name.startswith(_FAKE_SYMBOL_PREFIXES):
                        return f"top-level import of '{module}.{alias.name}' at line {stmt.lineno}"
    return None


def classify_module(source: str, path: str) -> str | None:
    """Classify one test module's source text as eligible or ineligible.

    Args:
        source: Full text of the module under classification.
        path: Repo-relative POSIX path used in reason messages.

    Returns:
        ``None`` when the module is dual-run eligible; otherwise a
        human-readable reason string describing why it was excluded.

    Raises:
        SyntaxError: Propagated when ``source`` fails to parse; callers
            should treat parse failures as their own ineligible reason.

    """
    tree = ast.parse(source, filename=path)
    pragma = _pragma_of(source)
    if pragma == PRAGMA_SKIP:
        return f"pragma '{PRAGMA_SKIP}'"
    import_reason = _reason_for_imports(tree)
    if import_reason is not None:
        if pragma == PRAGMA_ELIGIBLE:
            return None
        return import_reason
    for stmt in tree.body:
        reason = _reason_for_statement(stmt)
        if reason is not None:
            if pragma == PRAGMA_ELIGIBLE:
                return None
            return reason
    return None


def classify_tests(repo_root: Path) -> DualRunClassification:
    """Walk ``tests/**`` and partition every test module into eligibility sets.

    Modules under the browser tier directory (``tests/browser``) are excluded:
    they already run through the browser harness and never participate in the
    dual-run sweep. Test modules are parsed read-only; none are imported.

    Args:
        repo_root: Repository root containing the ``tests/`` tree.

    Returns:
        A :class:`DualRunClassification` with sorted repo-relative paths.

    """
    result = DualRunClassification()
    tests_dir = repo_root / "tests"
    if not tests_dir.is_dir():
        return result
    for path in sorted(tests_dir.rglob("test_*.py")):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        if rel.startswith(f"{BROWSER_TEST_DIR}/"):
            continue
        try:
            source = path.read_text(encoding="utf-8")
            reason = classify_module(source, rel)
        except SyntaxError as e:
            reason = f"syntax error at line {e.lineno}"
        except UnicodeDecodeError:
            reason = "file is not valid UTF-8"
        if reason is None:
            result.eligible.append(rel)
        else:
            result.ineligible[rel] = reason
    return result


def write_baseline(result: DualRunClassification, out_dir: Path) -> tuple[Path, Path]:
    """Persist a classification snapshot as reviewable baseline files.

    Args:
        result: Classification produced by :func:`classify_tests`.
        out_dir: Destination directory (created when missing).

    Returns:
        Tuple of the written ``eligible.txt`` and ``ineligible.json`` paths.

    """
    out_dir.mkdir(parents=True, exist_ok=True)
    eligible_path = out_dir / "eligible.txt"
    ineligible_path = out_dir / "ineligible.json"
    eligible_path.write_text(
        "".join(f"{path}\n" for path in sorted(result.eligible)),
        encoding="utf-8",
    )
    ineligible_path.write_text(
        json.dumps(dict(sorted(result.ineligible.items())), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return eligible_path, ineligible_path


def load_baseline(repo_root: Path) -> list[str]:
    """Read the committed baseline eligible-module inventory.

    Args:
        repo_root: Repository root containing ``tests/.dualrun/eligible.txt``.

    Returns:
        Sorted repo-relative eligible paths from the baseline file, or an
        empty list when the baseline does not exist yet.

    """
    baseline = repo_root / DUALRUN_BASELINE_DIR / "eligible.txt"
    if not baseline.is_file():
        return []
    return sorted(line.strip() for line in baseline.read_text(encoding="utf-8").splitlines() if line.strip())
