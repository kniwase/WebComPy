from __future__ import annotations

from tests.conftest import FakeBrowserModule, MockHistoryPort
from webcompy.ports._browser import _raw
from webcompy.ports._browser._history import BrowserHistoryPort
from webcompy.ports._history import HistoryPort


class RecordingScrollManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def on_push(self, from_path: str, to_path: str) -> None:
        self.calls.append(("push", from_path, to_path))

    def on_pop(self, from_path: str, to_path: str) -> None:
        self.calls.append(("pop", from_path, to_path))


class TestHistoryPortPushHook:
    def test_push_classification(self):
        hist = MockHistoryPort(mode="history")
        manager = RecordingScrollManager()
        hist.set_scroll_manager(manager)
        hist.navigate("/b", None)
        assert manager.calls == [("push", "/", "/b")]

    def test_hash_mode_strips_hash_prefix(self):
        hist = MockHistoryPort(mode="hash")
        manager = RecordingScrollManager()
        hist.set_scroll_manager(manager)
        hist.navigate("#/b", None)
        assert manager.calls == [("push", "/", "/b")]

    def test_same_value_navigation_does_not_notify(self):
        hist = MockHistoryPort(mode="history")
        manager = RecordingScrollManager()
        hist.set_scroll_manager(manager)
        hist.navigate("/", None)
        assert manager.calls == []

    def test_no_manager_registered(self):
        hist = MockHistoryPort(mode="history")
        hist.navigate("/b", None)
        assert hist.value == "/b"


class TestBrowserHistoryPortPopHook:
    def _make_port(
        self,
        monkeypatch,
        *,
        mode: str = "history",
        initial: str = "/",
        pathname: str = "/a",
        hash_val: str = "",
        state: object | None = None,
    ) -> tuple[FakeBrowserModule, BrowserHistoryPort]:
        fake = FakeBrowserModule()
        monkeypatch.setattr("webcompy.ports._browser._history.ENVIRONMENT", "pyscript")
        monkeypatch.setattr(_raw, "browser", fake)
        fake.window.location.pathname = pathname
        fake.window.location.hash = hash_val
        fake.window.history._state = state
        hist = BrowserHistoryPort.__new__(BrowserHistoryPort)
        hist._browser = fake
        HistoryPort.__init__(hist, initial, mode=mode)
        return fake, hist

    def test_pop_default_path(self, monkeypatch):
        _, hist = self._make_port(monkeypatch)
        manager = RecordingScrollManager()
        hist.set_scroll_manager(manager)
        hist._on_popstate(None)
        assert manager.calls == [("pop", "/", "/a")]

    def test_pop_hash_mode(self, monkeypatch):
        _, hist = self._make_port(monkeypatch, mode="hash", pathname="/", hash_val="/a")
        manager = RecordingScrollManager()
        hist.set_scroll_manager(manager)
        hist._on_popstate(None)
        assert manager.calls == [("pop", "/", "/a")]

    def test_pop_via_callback_does_not_fire_push(self, monkeypatch):
        _, hist = self._make_port(monkeypatch)
        hist.set_navigation_callback(lambda p, s: hist.navigate(p, s))
        manager = RecordingScrollManager()
        hist.set_scroll_manager(manager)
        hist._on_popstate(None)
        assert manager.calls == [("pop", "/", "/a")]

    def test_pop_without_manager(self, monkeypatch):
        _, hist = self._make_port(monkeypatch)
        hist._on_popstate(None)
        assert hist.value == "/a"
