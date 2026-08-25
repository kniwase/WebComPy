import queue
import threading

import pytest

from tests.browser import _driver
from tests.browser._driver import (
    BrowserHarnessDriver,
    append_param_index,
    classify_crash,
    sentinel_timeout_seconds,
    strip_param_suffix,
)


class TestClassifyCrash:
    @pytest.mark.parametrize(
        ("exc_text", "expected"),
        [
            ("Target page, context or browser has been closed", True),
            ("Page.evaluate: Target closed", True),
            ("Aborted(Assertion failed). Build with -s ASSERTIONS=1", True),
            ("TypeError: cannot read properties of undefined", False),
        ],
    )
    def test_exc_text(self, exc_text, expected):
        assert classify_crash(exc_text, []) is expected

    def test_wasm_abort_visible_only_in_console_tail(self):
        assert classify_crash("some evaluate error", ["Aborted(1). Build with -s"]) is True

    def test_plain_failure_is_not_a_crash(self):
        assert classify_crash("AssertionError", []) is False


def _bare_driver() -> BrowserHarnessDriver:
    driver = object.__new__(BrowserHarnessDriver)
    driver._base_url = "http://127.0.0.1:0/"
    driver._strict_console = False
    driver._console_messages = []
    driver._mailbox = queue.Queue()
    driver._boot_error = None
    driver._dead = threading.Event()
    driver._last_error = None
    driver._ready = threading.Event()
    return driver


class TestDeadWorkerFailFast:
    def test_call_raises_immediately_when_worker_dead(self):
        driver = _bare_driver()
        driver._last_error = RuntimeError("playwright exploded")
        driver._dead.set()

        with pytest.raises(RuntimeError, match="worker thread has exited"):
            driver._call(lambda page: None)

    def test_fail_fast_guard_passes_for_live_worker(self):
        driver = _bare_driver()

        driver._fail_fast_if_dead()

        assert driver._last_error is None

    def test_timeout_reports_hanging_page(self, monkeypatch):
        monkeypatch.setattr(_driver, "_CALL_TIMEOUT_BASE_SECONDS", 0.01)
        monkeypatch.setattr(_driver, "sentinel_timeout_seconds", lambda: 0.01)
        driver = _bare_driver()

        with pytest.raises(RuntimeError, match=r"did not respond.*hanging in-page test"):
            driver._call(lambda page: None)

    def test_timeout_reports_dead_worker(self, monkeypatch):
        monkeypatch.setattr(_driver, "_CALL_TIMEOUT_BASE_SECONDS", 0.01)
        monkeypatch.setattr(_driver, "sentinel_timeout_seconds", lambda: 0.01)
        driver = _bare_driver()
        # The worker dies while a request is already in flight.
        threading.Timer(0.005, driver._dead.set).start()

        with pytest.raises(RuntimeError, match=r"did not respond.*worker thread died"):
            driver._call(lambda page: None)


class TestParamIndexSuffix:
    def test_round_trip(self):
        suffixed = append_param_index("tests/browser/t.py::test_foo[a-b]", 2)

        node_id, index = strip_param_suffix(suffixed)

        assert node_id == "tests/browser/t.py::test_foo[a-b]"
        assert index == 2

    def test_no_suffix(self):
        node_id, index = strip_param_suffix("tests/browser/t.py::test_bar")

        assert node_id == "tests/browser/t.py::test_bar"
        assert index is None


def test_sentinel_timeout_default(monkeypatch):
    monkeypatch.delenv("WEBCOMPY_BROWSER_SENTINEL_TIMEOUT", raising=False)

    assert sentinel_timeout_seconds() == 120.0


def test_sentinel_timeout_env_override(monkeypatch):
    monkeypatch.setenv("WEBCOMPY_BROWSER_SENTINEL_TIMEOUT", "15")

    assert sentinel_timeout_seconds() == 15.0


def test_sentinel_timeout_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("WEBCOMPY_BROWSER_SENTINEL_TIMEOUT", "abc")

    assert sentinel_timeout_seconds() == 120.0
