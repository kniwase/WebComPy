"""Browser test tier: tests execute inside a real PyScript runtime via the harness."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

_BROWSER_TARGET_RE = re.compile(r"(^|/)tests/browser(/|$)")
_BROWSER_DIR = Path(__file__).resolve().parent


def _invocation_targets_browser_tier(args: list[str]) -> bool:
    return any(_BROWSER_TARGET_RE.search(arg.replace("\\", "/").rstrip("/")) for arg in args)


def pytest_configure(config: pytest.Config) -> None:
    if os.environ.get("WEBCOMPY_RUN_BROWSER") == "1":
        return
    if _invocation_targets_browser_tier(list(config.args)):
        raise pytest.UsageError(
            "Browser tests are gated by the WEBCOMPY_RUN_BROWSER=1 environment variable. "
            "Run via scripts/run-browser-tests.sh, or for advanced direct invocation: "
            "WEBCOMPY_RUN_BROWSER=1 uv run pytest tests/browser/..."
        )


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if item.path.is_relative_to(_BROWSER_DIR):
            item.add_marker(pytest.mark.browser)


def _format_remote_failure(result: dict) -> str:
    sections = [f"browser test failed in-page: {result.get('exc_type')}"]
    if result.get("traceback"):
        sections.append(result["traceback"])
    if result.get("stdout"):
        sections.append(f"--- captured stdout ---\n{result['stdout']}")
    if result.get("stderr"):
        sections.append(f"--- captured stderr ---\n{result['stderr']}")
    delta = result.get("console_error_delta") or []
    if delta:
        sections.append("--- browser console errors ---\n" + "\n".join(delta))
    return "\n".join(sections)


def _parametrize_index(pyfuncitem: pytest.Function) -> int | None:
    """Derive the machine suffix index from the item's resolved parametrize call."""
    callspec = getattr(pyfuncitem, "callspec", None)
    if callspec is None:
        return None
    marks = [mark for mark in getattr(pyfuncitem.function, "pytestmark", []) if mark.name == "parametrize"]
    if not marks:
        return None
    if len(marks) > 1:
        raise RuntimeError("stacked @pytest.mark.parametrize marks are not supported in the browser test tier")
    raw_names, values = marks[0].args
    names = [name.strip() for name in raw_names.split(",")] if isinstance(raw_names, str) else list(raw_names)
    actual = tuple(callspec.params[name] for name in names)
    for index, value in enumerate(values):
        candidate = (value,) if len(names) == 1 else tuple(value)
        expected = (actual[0],) if len(names) == 1 else actual
        if candidate == expected:
            return index
    raise RuntimeError(f"could not match callspec params {actual!r} to parametrize values")


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    if "browser" not in pyfuncitem.keywords:
        return None
    driver = getattr(pyfuncitem.session, "_browser_driver", None)
    if driver is None:
        raise RuntimeError(
            "browser harness driver was not initialized; the autouse "
            "browser_harness fixture should have run before this test"
        )
    test_id = pyfuncitem.nodeid
    index = _parametrize_index(pyfuncitem)
    if index is not None:
        from tests.browser._driver import append_param_index

        test_id = append_param_index(test_id, index)
    from webcompy_testing.browser_runner import normalize_traceback

    result = driver.run_one(test_id)
    if result.get("traceback"):
        result["traceback"] = normalize_traceback(result["traceback"])
    status = result.get("status")
    if status == "passed":
        return True
    if status == "skipped":
        pytest.skip(result.get("traceback") or "skipped inside the harness page")
    raise AssertionError(_format_remote_failure(result))


@pytest.fixture(scope="session")
def app() -> None:
    """Placeholder for the in-page ``app`` fixture resolved by the harness runner.

    The test function is executed inside the PyScript page, never locally;
    this exists only so standard pytest fixture resolution succeeds.
    """
    return None


@pytest.fixture(scope="session")
def dom_root() -> None:
    """Placeholder for the in-page ``dom_root`` fixture resolved by the harness runner."""
    return None


@pytest.fixture(scope="session", autouse=True)
def browser_harness(request: pytest.FixtureRequest):
    from pathlib import Path

    from tests.browser._driver import BrowserHarnessDriver
    from webcompy_cli._browser_test_harness import (
        create_harness_app,
        reserve_port,
        serve_harness,
        shutdown_harness,
    )

    repo_root = Path.cwd()
    cache_dir = repo_root / ".tmp" / "webcompy-browser-harness"
    cache_dir.mkdir(parents=True, exist_ok=True)

    port = reserve_port()
    base_url = f"http://127.0.0.1:{port}/"
    harness = create_harness_app(repo_root, cache_dir, base_url=base_url)
    process = serve_harness(harness, port=port)
    driver = BrowserHarnessDriver(base_url)
    request.session._browser_driver = driver  # type: ignore[attr-defined]
    try:
        yield driver
    finally:
        request.session._browser_driver = None  # type: ignore[attr-defined]
        driver.close()
        shutdown_harness(process)
