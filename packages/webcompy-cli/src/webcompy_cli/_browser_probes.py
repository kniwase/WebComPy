"""AST classifier and dual-run sweep utilities for ``tests/`` modules.

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
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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

    Parse failures of ``source`` propagate as :class:`SyntaxError`; callers
    should treat them as their own ineligible reason.

    Args:
        source: Full text of the module under classification.
        path: Repo-relative POSIX path used in reason messages.

    Returns:
        ``None`` when the module is dual-run eligible; otherwise a
        human-readable reason string describing why it was excluded.

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


_DUALRUN_ARTIFACT_NAME = "browser-dualrun.json"
_DISPLAY_SUFFIX_RE = re.compile(r"\[[^\[\]]*\]$")


@dataclass
class DualRunSweepResult:
    """Outcome of one CPython-vs-PyScript dual-run sweep.

    Attributes:
        eligible_count: Number of eligible modules the sweep attempted.
        buckets: Bucketed test ids keyed ``both-pass``, ``CPython-only-fail``,
            ``PyScript-only-fail``, and ``both-fail``.
        cpython_map: Mapping of CPython node id to raw outcome
            (``passed`` / ``failed`` / ``skipped``).
        pyscript_map: Same-shaped mapping collected in-page, keyed by the
            original CPython node id.
        duration_ms: Total sweep wall time in milliseconds.
        error: Infrastructure error message when the CPython side could not
            produce a report; ``None`` on a structurally complete sweep.

    """

    eligible_count: int
    buckets: dict[str, list[str]] = field(default_factory=dict)
    cpython_map: dict[str, str] = field(default_factory=dict)
    pyscript_map: dict[str, str] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: str | None = None


def convert_cpython_id(nodeid: str, param_indices: dict[str, int]) -> str:
    """Convert a CPython pytest node id into an in-page runner test id.

    The trailing display suffix (``[param value]``) is stripped and replaced
    with the machine-readable index form (``[p<index>]``) expected by the
    in-page runner.

    Args:
        nodeid: CPython pytest node id, optionally carrying a display
            parametrize suffix.
        param_indices: Mapping of suffix-stripped node id to its parametrize
            index within the declared values list.

    Returns:
        The equivalent in-page test id.

    """
    match = _DISPLAY_SUFFIX_RE.search(nodeid)
    stripped = nodeid[: match.start()] if match else nodeid
    index = param_indices.get(stripped)
    if index is not None:
        return f"{stripped}[p{index}]"
    return stripped


def diff_outcomes(cpython_map: dict[str, str], pyscript_map: dict[str, str]) -> dict[str, list[str]]:
    """Bucket paired outcomes from both interpreters into a divergence diff.

    Test ids whose outcome is ``skipped`` on either side are excluded from the
    buckets but remain present in the raw maps written to the artifact.

    Args:
        cpython_map: Node-id-to-outcome mapping collected under CPython.
        pyscript_map: Same-shaped mapping collected inside the harness page.

    Returns:
        Buckets keyed ``both-pass``, ``CPython-only-fail``,
        ``PyScript-only-fail``, and ``both-fail`` with sorted test ids.

    """
    buckets: dict[str, list[str]] = {
        "both-pass": [],
        "CPython-only-fail": [],
        "PyScript-only-fail": [],
        "both-fail": [],
    }
    for test_id in sorted(set(cpython_map) & set(pyscript_map)):
        cpython = cpython_map[test_id]
        pyscript = pyscript_map[test_id]
        if cpython == "skipped" or pyscript == "skipped":
            continue
        if cpython == "passed" and pyscript == "passed":
            buckets["both-pass"].append(test_id)
        elif cpython == "passed":
            buckets["PyScript-only-fail"].append(test_id)
        elif pyscript == "passed":
            buckets["CPython-only-fail"].append(test_id)
        else:
            buckets["both-fail"].append(test_id)
    return buckets


def write_dualrun_artifact(result: DualRunSweepResult, artifacts_dir: Path) -> Path:
    """Write the bucketed dual-run diff artifact for one sweep invocation.

    Args:
        result: Sweep outcome to serialize.
        artifacts_dir: Destination directory (created when missing).

    Returns:
        The path of the written ``browser-dualrun.json`` artifact.

    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / _DUALRUN_ARTIFACT_NAME
    payload = {
        "eligible_count": result.eligible_count,
        "buckets": {name: sorted(ids) for name, ids in result.buckets.items()},
        "cpython_map": dict(sorted(result.cpython_map.items())),
        "pyscript_map": dict(sorted(result.pyscript_map.items())),
        "duration_ms": round(result.duration_ms, 3),
    }
    if result.error is not None:
        payload["error"] = result.error
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def run_dualrun_sweep(
    *,
    repo_root: Path,
    driver: Any,
    artifacts_dir: Path | None = None,
    report_path: Path | None = None,
) -> DualRunSweepResult:
    """Execute the eligible subset under both interpreters and diff results.

    The CPython side runs a subprocess pytest over the classified eligible
    modules using the dual-run report plugin; the PyScript side dispatches the
    same test ids through the live harness driver. The sweep is informational:
    infrastructure failures are recorded in :attr:`DualRunSweepResult.error`
    instead of raising, so callers never need to fail a session because of it.

    Args:
        repo_root: Repository root containing the ``tests/`` tree.
        driver: Live browser harness driver exposing ``run_one(test_id)``
            returning the in-page JSON result string.
        artifacts_dir: Directory for ``browser-dualrun.json``; defaults to
            ``<repo_root>/artifacts``.
        report_path: Where the CPython plugin writes its outcome JSON;
            defaults to a scratch file under ``<repo_root>/.tmp``.

    Returns:
        A :class:`DualRunSweepResult` describing the paired outcomes.

    """
    started = time.perf_counter()
    destination = artifacts_dir or repo_root / "artifacts"
    scratch = report_path or repo_root / ".tmp" / "dualrun-cpython.json"
    classification = classify_tests(repo_root)
    result = DualRunSweepResult(eligible_count=len(classification.eligible))
    if not classification.eligible:
        result.duration_ms = (time.perf_counter() - started) * 1000
        write_dualrun_artifact(result, destination)
        return result

    outcomes, indices = _collect_cpython_outcomes(repo_root, classification.eligible, scratch)
    if outcomes is None:
        result.error = f"CPython collection failed; see {scratch} diagnostics in the subprocess log"
        result.duration_ms = (time.perf_counter() - started) * 1000
        write_dualrun_artifact(result, destination)
        return result

    result.cpython_map = outcomes
    total = len(outcomes)
    for progress, nodeid in enumerate(sorted(outcomes), start=1):
        converted = convert_cpython_id(nodeid, indices)
        try:
            payload = driver.run_one(converted)
            if isinstance(payload, (str, bytes)):
                payload = json.loads(payload)
            status = str(payload.get("status", "failed"))
        except RuntimeError as e:
            if "worker thread" in str(e):
                # Driver is dead; nothing further can execute in-page.
                for remaining in sorted(outcomes)[progress - 1 :]:
                    result.pyscript_map[remaining] = "skipped"
                break
            status = "failed"
        except Exception:
            status = "failed"
        result.pyscript_map[nodeid] = status
        if progress % 25 == 0 or progress == total:
            print(f"[browser-dualrun] in-page progress {progress}/{total}", flush=True)

    result.buckets = diff_outcomes(result.cpython_map, result.pyscript_map)
    result.duration_ms = (time.perf_counter() - started) * 1000
    write_dualrun_artifact(result, destination)
    return result


def _collect_cpython_outcomes(
    repo_root: Path,
    eligible: list[str],
    report_path: Path,
) -> tuple[dict[str, str] | None, dict[str, int]]:
    """Collect CPython outcomes for the eligible modules via a pytest subprocess.

    A nonzero pytest exit code caused by failing tests is expected and not an
    infrastructure failure; only a missing or malformed report is.

    Args:
        repo_root: Repository root used as the pytest working directory.
        eligible: Repo-relative eligible module paths to run.
        report_path: Destination of the dual-run plugin's JSON report.

    Returns:
        Tuple of the outcome map (or ``None`` on infrastructure failure) and
        the nodeid-to-parametrize-index map.

    """
    import os
    import subprocess
    import sys

    report_path.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "WEBCOMPY_DUALRUN_REPORT": str(report_path)}
    command = [
        sys.executable,
        "-m",
        "pytest",
        *sorted(eligible),
        "-p",
        "webcompy_cli._dualrun_pytest_plugin",
        "-q",
        "--tb=no",
        "--no-header",
    ]
    completed = subprocess.run(command, cwd=repo_root, env=env, capture_output=True, check=False)
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        outcomes = {str(k): str(v) for k, v in data.get("outcomes", {}).items()}
        indices = {str(k): int(v) for k, v in data.get("param_indices", {}).items()}
    except (OSError, json.JSONDecodeError):
        print(
            "[browser-dualrun] warning: CPython subprocess produced no usable report "
            f"(exit={completed.returncode}); stderr tail:\n{completed.stderr.decode(errors='replace')[-2000:]}",
            flush=True,
        )
        return None, {}
    return outcomes, indices
