"""Browser test tier: tests execute inside a real PyScript runtime via the harness."""

from __future__ import annotations

import os
import re

import pytest

_BROWSER_TARGET_RE = re.compile(r"(^|/)tests/browser(/|$)")


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


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    if "browser" not in pyfuncitem.keywords:
        return None
    driver = getattr(pyfuncitem.session, "_browser_driver", None)
    if driver is None:
        driver = pyfuncitem.session.getfixturevalue("browser_harness")
    test_id = pyfuncitem.nodeid
    callspec = getattr(pyfuncitem, "callspec", None)
    if callspec is not None:
        from tests.browser._driver import append_param_index

        test_id = append_param_index(test_id, callspec.index)
    result = driver.run_one(test_id)
    status = result.get("status")
    if status == "passed":
        return True
    if status == "skipped":
        pytest.skip(result.get("traceback") or "skipped inside the harness page")
    raise AssertionError(_format_remote_failure(result))


@pytest.fixture(scope="session")
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
    process = serve_harness(harness.asgi, port=port)
    driver = BrowserHarnessDriver(base_url)
    request.session._browser_driver = driver  # type: ignore[attr-defined]
    try:
        yield driver
    finally:
        request.session._browser_driver = None  # type: ignore[attr-defined]
        driver.close()
        shutdown_harness(process)
