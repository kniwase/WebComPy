"""Pytest plugin recording per-test outcomes for the dual-run sweep.

Loaded in the CPython-side subprocess via
``pytest -p webcompy_cli._dualrun_pytest_plugin``. When the environment
variable ``WEBCOMPY_DUALRUN_REPORT`` points at a file path, the plugin writes
a JSON report of ``{nodeid: outcome}`` plus a nodeid-to-parametrize-index map
at session finish; without the variable it stays inert so ordinary runs are
unaffected.
"""

from __future__ import annotations

import json
import os
import re

import pytest

_DISPLAY_SUFFIX_RE = re.compile(r"\[[^\[\]]*\]$")
_OUTCOME_PRECEDENCE = {"failed": 3, "skipped": 2, "passed": 1}


def _parametrize_index_of(item) -> int | None:
    """Derive the machine parametrize index for one collected item.

    Mirrors the browser-tier conftest algorithm: match the item's resolved
    callspec params against the declared values list of its single
    ``@pytest.mark.parametrize`` mark.

    Args:
        item: A collected pytest item.

    Returns:
        The zero-based index within the declared values, or ``None`` when the
        item is not parametrized or the values cannot be matched uniquely.

    """
    callspec = getattr(item, "callspec", None)
    if callspec is None:
        return None
    marks = [mark for mark in getattr(item.function, "pytestmark", []) if mark.name == "parametrize"]
    if not marks:
        return None
    raw_names, values = marks[0].args
    names = (
        [name.strip() for name in raw_names.split(",")] if isinstance(raw_names, str) else [str(n) for n in raw_names]
    )
    actual = tuple(callspec.params[name] for name in names)
    matches: list[int] = []
    for index, value in enumerate(values):
        candidate = (value,) if len(names) == 1 else tuple(value)
        expected = (actual[0],) if len(names) == 1 else actual
        if candidate == expected:
            matches.append(index)
    return matches[0] if len(matches) == 1 else None


def pytest_collection_finish(session) -> None:
    """Record every collected item's node id and parametrize index.

    Args:
        session: The pytest session that finished collection.

    Returns:
        ``None``.

    """
    indices: dict[str, int] = {}
    for item in session.items:
        index = _parametrize_index_of(item)
        if index is not None:
            match = _DISPLAY_SUFFIX_RE.search(item.nodeid)
            stripped = item.nodeid[: match.start()] if match else item.nodeid
            indices[stripped] = index
    session._dualrun_param_indices = indices  # type: ignore[attr-defined]
    session._dualrun_outcomes = {}  # type: ignore[attr-defined]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Merge each phase's report into the node-id outcome map.

    Outcomes across setup/call/teardown merge with precedence
    failed > skipped > passed so a teardown failure after a passing call is
    still surfaced.

    Args:
        item: The executing pytest item.
        call: The phase context (setup, call, or teardown).

    Yields:
        The wrapped hook result carrying the phase report.

    """
    outcome = yield
    report = outcome.get_result()
    outcomes = getattr(item.session, "_dualrun_outcomes", None)
    if outcomes is None:
        return
    existing = outcomes.get(report.nodeid)
    if existing is None or _OUTCOME_PRECEDENCE.get(report.outcome, 0) > _OUTCOME_PRECEDENCE.get(existing, 0):
        outcomes[report.nodeid] = report.outcome


def pytest_sessionfinish(session, exitstatus) -> None:
    """Write the recorded outcomes and indices when a report path is set.

    Args:
        session: The finishing pytest session.
        exitstatus: Pytest's internal exit status code (unused).

    Returns:
        ``None``.

    """
    target = os.environ.get("WEBCOMPY_DUALRUN_REPORT")
    if not target:
        return
    payload = {
        "outcomes": dict(getattr(session, "_dualrun_outcomes", {})),
        "param_indices": dict(getattr(session, "_dualrun_param_indices", {})),
    }
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
