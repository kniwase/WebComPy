from __future__ import annotations

import logging
from typing import Literal

from tests.conftest import FakeBrowserModule, MockHistoryPort
from webcompy_server.ports._history import ServerHistoryPort


def _make_browser_port(mode: Literal["hash", "history"], base_url: str = ""):
    from webcompy.ports._browser._history import BrowserHistoryPort

    port = BrowserHistoryPort.__new__(BrowserHistoryPort)
    port._browser = FakeBrowserModule()
    port._mode = mode
    port._base_url = base_url.strip().strip("/")
    return port


class TestBuildUrl:
    def test_hash_mode(self):
        assert _make_browser_port("hash")._build_url("/about") == "#/about/"

    def test_hash_mode_root(self):
        assert _make_browser_port("hash")._build_url("/") == "#/"

    def test_hash_mode_query_preserved(self):
        assert _make_browser_port("hash")._build_url("/s/?q=1") == "#/s/?q=1"

    def test_history_mode_no_base(self):
        assert _make_browser_port("history")._build_url("/about") == "/about/"

    def test_history_mode_with_base(self):
        assert _make_browser_port("history", "/myapp")._build_url("/about") == "/myapp/about/"

    def test_history_mode_base_slashes_normalized(self):
        assert _make_browser_port("history", "/myapp/")._build_url("/about") == "/myapp/about/"


class TestNormalizePath:
    def test_hash_mode(self):
        port = _make_browser_port("hash")
        assert port._normalize_path("#/about/") == "/about/"
        assert port._normalize_path("#/about") == "/about/"
        assert port._normalize_path("/about/") == "/about/"

    def test_history_mode_no_base(self):
        port = _make_browser_port("history")
        assert port._normalize_path("/about") == "/about/"
        assert port._normalize_path("/about/") == "/about/"
        assert port._normalize_path("/") == "/"

    def test_history_mode_with_base(self):
        port = _make_browser_port("history", "/myapp")
        assert port._normalize_path("/myapp/about/") == "/about/"
        assert port._normalize_path("/myapp/about") == "/about/"
        assert port._normalize_path("/myapp/") == "/"
        assert port._normalize_path("/myapp") == "/"
        assert port._normalize_path("/myappx/about/") == "/myappx/about/"

    def test_query_preserved(self):
        port = _make_browser_port("hash")
        assert port._normalize_path("/search?q=1") == "/search/?q=1"


class TestPopstateNormalization:
    def test_on_popstate_passes_normalized_path_to_callback_and_scroll_manager(self):
        from unittest.mock import MagicMock

        port = _make_browser_port("history", "/myapp")
        port._value = "/"
        received: list[tuple[str, dict | None]] = []
        port.set_navigation_callback(lambda p, s: received.append((p, s)))
        manager = MagicMock()
        port._scroll_manager = manager
        port._browser.window.location.pathname = "/myapp/about/"
        port._browser.window.location.search = ""
        port._on_popstate(None)
        assert received == [("/about/", None)]
        manager.on_pop.assert_called_once_with("/", "/about/")

    def test_on_popstate_default_path_normalizes(self):
        from webcompy.ports._history import HistoryPort

        port = _make_browser_port("hash")
        HistoryPort.__init__(port, "/", mode="hash")
        port.set_navigation_callback(None)
        port._browser.window.location.hash = "#/about"
        port._on_popstate(None)
        assert port._value == "/about/"


class TestInitialPathNormalization:
    def test_ctor_initial_path_normalized(self, monkeypatch):
        from webcompy.ports._browser._history import BrowserHistoryPort

        fake = FakeBrowserModule()
        monkeypatch.setattr("webcompy.ports._browser._history.ENVIRONMENT", "pyscript")
        monkeypatch.setattr("webcompy.ports._browser._history._raw_browser", fake)
        fake.window.location.pathname = "/scroll-long"
        fake.window.location.search = ""
        fake.window.location.hash = ""
        hist = BrowserHistoryPort(mode="history")
        assert hist.value == "/scroll-long/"

    def test_ctor_initial_path_with_base_url_normalized(self, monkeypatch):
        from webcompy.ports._browser._history import BrowserHistoryPort

        fake = FakeBrowserModule()
        monkeypatch.setattr("webcompy.ports._browser._history.ENVIRONMENT", "pyscript")
        monkeypatch.setattr("webcompy.ports._browser._history._raw_browser", fake)
        fake.window.location.pathname = "/myapp/about"
        fake.window.location.search = ""
        fake.window.location.hash = ""
        hist = BrowserHistoryPort(mode="history", base_url="/myapp")
        assert hist.value == "/about/"


class TestBrowserPushReplace:
    def test_push_url_calls_pushState(self):
        port = _make_browser_port("hash")
        port.push_url("/about", {"k": "v"})
        port._browser.window.history.pushState.assert_called_once_with({"k": "v"}, None, "#/about/")

    def test_replace_url_calls_replaceState(self):
        port = _make_browser_port("history", "/myapp")
        port.replace_url("/login", None)
        port._browser.window.history.replaceState.assert_called_once_with(None, None, "/myapp/login/")

    def test_non_serializable_state_becomes_none(self, caplog):
        port = _make_browser_port("hash")
        with caplog.at_level(logging.WARNING):
            port.push_url("/about", {"bad": object()})  # type: ignore[dict-item]
        port._browser.window.history.pushState.assert_called_once_with(None, None, "#/about/")
        assert "json-serializable" in caplog.text


class TestNoOpPorts:
    def test_server_port_noop(self):
        port = ServerHistoryPort(mode="history")
        port.push_url("/x", None)
        port.replace_url("/x", None)

    def test_fake_recording(self):
        port = MockHistoryPort(mode="hash")
        port.push_url("/a", None)
        port.replace_url("/b", {"s": 1})
        assert port.pushed_urls == [("/a", None)]
        assert port.replaced_urls == [("/b", {"s": 1})]
