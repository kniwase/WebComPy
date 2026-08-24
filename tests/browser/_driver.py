"""Playwright driver dispatching browser test ids to the harness page.

All Playwright objects live on a dedicated worker thread: the sync Playwright
API leaves an event loop running in whichever thread starts it, which would
poison subsequent asyncio-based unit tests in the same pytest session.
"""

from __future__ import annotations

import json
import os
import queue
import re
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

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


_STOP = object()


class BrowserHarnessDriver:
    """Owns the Playwright browser/page on a worker thread and dispatches ``run_one``."""

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
        self._mailbox: queue.Queue[tuple[Callable[[Any], Any], queue.Queue]] = queue.Queue()
        self._boot_error: BaseException | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._worker_main, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=sentinel_timeout_seconds() + 60):
            raise RuntimeError(f"browser worker thread failed to boot. Boot error: {self._boot_error!r}")
        if self._boot_error is not None:
            raise self._boot_error

    @property
    def console_messages(self) -> list[str]:
        return list(self._console_messages)

    def console_tail(self, size: int = _CRASH_TAIL_SIZE) -> list[str]:
        return self._console_messages[-size:]

    def run_one(self, test_id: str) -> dict:
        """Dispatch one test id to the page and normalize its JSON result."""
        start = len(self._console_messages)
        raw = self._call(lambda page: self._evaluate(page, test_id))
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

    def close(self) -> None:
        self._mailbox.put((_STOP, queue.Queue()))
        self._thread.join(timeout=30)

    def _call(self, fn: Callable[[Any], Any]) -> Any:
        result_q: queue.Queue = queue.Queue()
        self._mailbox.put((fn, result_q))
        kind, payload = result_q.get(timeout=sentinel_timeout_seconds() * 2 + 120)
        if kind == "err":
            raise payload
        return payload

    def _worker_main(self) -> None:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context()
                page = self._open_page(context)
                self._ready.set()

                def _rebuild() -> Any:
                    with suppress(Exception):
                        context.close()
                    fresh_context = browser.new_context()
                    return self._open_page(fresh_context), fresh_context

                while True:
                    item = self._mailbox.get()
                    fn = item[0]
                    if fn is _STOP:
                        with suppress(Exception):
                            browser.close()
                        return
                    result_q: queue.Queue = item[1]
                    try:
                        result_q.put(("ok", fn(page)))
                    except Exception as e:
                        tail = list(self._console_messages)
                        if classify_crash(str(e), tail):
                            page, context = _rebuild()
                            e = BrowserCrashError(console_tail=tail[-_CRASH_TAIL_SIZE:])
                        result_q.put(("err", e))
        except BaseException as e:
            self._boot_error = e
            self._ready.set()

    def _open_page(self, context: Any) -> Any:
        page = context.new_page()
        page.on("console", self._on_console)
        page.goto(f"{self._base_url}/testharness")
        timeout_ms = int(sentinel_timeout_seconds() * 1000)
        try:
            page.wait_for_selector(_SENTINEL_SELECTOR, state="attached", timeout=timeout_ms)
        except Exception as e:
            tail = self.console_tail()
            raise RuntimeError(f"Harness page did not become ready within {timeout_ms}ms. Console tail:\n{tail}") from e
        return page

    def _evaluate(self, page: Any, test_id: str) -> str:
        return page.evaluate("id => window.__webcompy_test__.run_one(id)", test_id)

    def _on_console(self, message: Any) -> None:
        if message.type == "error":
            self._console_messages.append(message.text)


_PARAM_SUFFIX_RE = re.compile(r"\[p(\d+)\]$")


def append_param_index(node_id: str, index: int) -> str:
    """Append the machine-readable parametrize suffix to a pytest node id."""
    return f"{node_id}[p{index}]"


def strip_param_suffix(test_id: str) -> tuple[str, int | None]:
    match = _PARAM_SUFFIX_RE.search(test_id)
    if match is None:
        return test_id, None
    return test_id[: match.start()], int(match.group(1))
