"""Playwright driver dispatching browser test ids to the harness page."""

from __future__ import annotations

import json
import os
import re
from contextlib import suppress
from dataclasses import dataclass, field

from playwright.sync_api import ConsoleMessage, Page, sync_playwright

_SENTINEL_SELECTOR = "html[data-webcompy-test-ready='1']"
_DEFAULT_SENTINEL_TIMEOUT_SECONDS = 120.0
_CRASH_MARKERS = (
    "target closed",
    "target page closed",
    "page closed",
    "context or browser has been closed",
    "aborted",
    "out of memory",
    "runtime exited",
)
_CRASH_TAIL_SIZE = 20


def sentinel_timeout_seconds() -> float:
    """Return the readiness-sentinel timeout configured via the environment."""
    raw = os.environ.get("WEBCOMPY_BROWSER_SENTINEL_TIMEOUT")
    try:
        return float(raw) if raw else _DEFAULT_SENTINEL_TIMEOUT_SECONDS
    except ValueError:
        return _DEFAULT_SENTINEL_TIMEOUT_SECONDS


def classify_crash(exc_text: str, console_tail: list[str]) -> bool:
    """Return True when an evaluate failure looks like a page/wasm crash."""
    haystack = exc_text.lower()
    if any(marker in haystack for marker in _CRASH_MARKERS):
        return True
    console_text = "\n".join(console_tail).lower()
    return any(marker in console_text for marker in ("aborted(", "runtime exited", "out of memory"))


def normalize_traceback_paths(text: str) -> str:
    """Defensively rewrite Emscripten FS paths in driver-received tracebacks."""
    rewrites = (
        ("/home/pyodide/tests/browser/", "tests/browser/"),
        ("/home/pyodide/_wc_src/webcompy/", "packages/webcompy/src/webcompy/"),
        (
            "/home/pyodide/_wc_src/webcompy_testing/",
            "packages/webcompy-testing/src/webcompy_testing/",
        ),
        (
            "/home/pyodide/_wc_src/webcompy_server/",
            "packages/webcompy-server/src/webcompy_server/",
        ),
    )
    for mounted, repo_relative in rewrites:
        text = text.replace(mounted, repo_relative)
    return text


@dataclass
class BrowserCrashError(RuntimeError):
    """Raised when the harness page crashed while executing a test."""

    console_tail: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        tail = "\n".join(self.console_tail[-_CRASH_TAIL_SIZE:])
        return f"browser page crashed during test. Console tail:\n{tail}"


class BrowserHarnessDriver:
    """Owns the Playwright browser/page and executes ``run_one`` dispatches."""

    def __init__(
        self,
        base_url: str,
        *,
        strict_console: bool | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._strict_console = (
            os.environ.get("WEBCOMPY_BROWSER_STRICT_CONSOLE") == "1" if strict_console is None else strict_console
        )
        self._console_messages: list[str] = []
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context()
        self.page: Page | None = None
        self.open()

    @property
    def console_messages(self) -> list[str]:
        return list(self._console_messages)

    def open(self) -> Page:
        if self.page is not None:
            return self.page
        page = self._context.new_page()
        page.on("console", self._on_console)
        page.goto(f"{self._base_url}/testharness")
        timeout_ms = int(sentinel_timeout_seconds() * 1000)
        try:
            page.wait_for_selector(_SENTINEL_SELECTOR, state="attached", timeout=timeout_ms)
        except Exception as e:
            tail = self.console_tail()
            raise RuntimeError(f"Harness page did not become ready within {timeout_ms}ms. Console tail:\n{tail}") from e
        self.page = page
        return page

    def restart(self) -> Page:
        """Tear down and relaunch the page (and context), then wait for the sentinel."""
        self.close_page()
        with suppress(Exception):
            self._context.close()
        self._context = self._browser.new_context()
        return self.open()

    def close_page(self) -> None:
        if self.page is not None:
            with suppress(Exception):
                self.page.close()
            self.page = None

    def console_tail(self, size: int = _CRASH_TAIL_SIZE) -> list[str]:
        return self._console_messages[-size:]

    def run_one(self, test_id: str) -> dict:
        """Dispatch one test id to the page and normalize its JSON result."""
        assert self.page is not None
        start = len(self._console_messages)
        try:
            raw = self.page.evaluate("id => window.__webcompy_test__.run_one(id)", test_id)
        except Exception as e:
            tail = self._console_messages[start:] or self._console_messages
            if classify_crash(str(e), tail):
                self.restart()
                raise BrowserCrashError(console_tail=list(tail)) from e
            raise
        result = json.loads(raw)
        if not result.get("console_error_delta"):
            result["console_error_delta"] = [message for message in self._console_messages[start:]]
        if self._strict_console and result["status"] == "passed":
            delta = result.get("console_error_delta") or []
            if delta:
                result["status"] = "failed"
                result["exc_type"] = "ConsoleError"
                result["traceback"] = "console errors captured during a passing test:\n" + "\n".join(delta)
        return result

    def _on_console(self, message: ConsoleMessage) -> None:
        if message.type == "error":
            self._console_messages.append(message.text)

    def close(self) -> None:
        self.close_page()
        for closer in (
            lambda: self._context.close(),
            lambda: self._browser.close(),
            lambda: self._playwright.stop(),
        ):
            with suppress(Exception):
                closer()


_PARAM_SUFFIX_RE = re.compile(r"\[p(\d+)\]$")


def append_param_index(node_id: str, index: int) -> str:
    """Append the machine-readable parametrize suffix to a pytest node id."""
    return f"{node_id}[p{index}]"


def strip_param_suffix(test_id: str) -> tuple[str, int | None]:
    match = _PARAM_SUFFIX_RE.search(test_id)
    if match is None:
        return test_id, None
    return test_id[: match.start()], int(match.group(1))
