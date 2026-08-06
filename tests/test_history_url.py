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
