from __future__ import annotations

from typing import Any

from tests.conftest import FakeBrowserModule, MockHistoryPort
from webcompy.ports._browser import _raw
from webcompy.ports._browser._history import BrowserHistoryPort
from webcompy.ports._history import HistoryPort
from webcompy.ports._host import HostPort
from webcompy.router._scroll import BrowserScrollManager


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
        assert manager.calls == [("pop", "/", "/a/")]

    def test_pop_hash_mode(self, monkeypatch):
        _, hist = self._make_port(monkeypatch, mode="hash", pathname="/", hash_val="/a")
        manager = RecordingScrollManager()
        hist.set_scroll_manager(manager)
        hist._on_popstate(None)
        assert manager.calls == [("pop", "/", "/a/")]

    def test_pop_via_callback_does_not_fire_push(self, monkeypatch):
        _, hist = self._make_port(monkeypatch)
        hist.set_navigation_callback(lambda p, s: hist.navigate(p, s))
        manager = RecordingScrollManager()
        hist.set_scroll_manager(manager)
        hist._on_popstate(None)
        assert manager.calls == [("pop", "/", "/a/")]

    def test_pop_without_manager(self, monkeypatch):
        _, hist = self._make_port(monkeypatch)
        hist._on_popstate(None)
        assert hist.value == "/a/"


class FakeDocumentElement:
    def __init__(self, scroll_height: int) -> None:
        self.scrollHeight = scroll_height


class FakeDocument:
    def __init__(self, scroll_height: int) -> None:
        self.documentElement = FakeDocumentElement(scroll_height)


class FakeHistory:
    def __init__(self) -> None:
        self.scrollRestoration = "auto"


class FakeScrollWindow:
    def __init__(self, *, scroll_height: int = 10000, inner_height: int = 1000) -> None:
        self.scrollX = 0
        self.scrollY = 0
        self.innerHeight = inner_height
        self.document = FakeDocument(scroll_height)
        self.history = FakeHistory()
        self.scroll_calls: list[tuple[int, int]] = []

    def scrollTo(self, x: int, y: int) -> None:
        self.scroll_calls.append((x, y))


class QueueHostPort(HostPort):
    def __init__(self) -> None:
        self.queue: list = []

    def schedule_macro_task(self, callback) -> None:
        self.queue.append(callback)

    def run_next(self) -> None:
        self.queue.pop(0)()

    def run_all(self) -> None:
        while self.queue:
            self.run_next()

    def create_js_global_getter(self, *args: Any, **kwargs: Any) -> Any:
        return lambda: None


class TestBrowserScrollManager:
    def test_init_sets_manual(self):
        window = FakeScrollWindow()
        BrowserScrollManager(QueueHostPort(), window)
        assert window.history.scrollRestoration == "manual"

    def test_save_on_push(self):
        window = FakeScrollWindow()
        window.scrollY = 500
        host = QueueHostPort()
        manager = BrowserScrollManager(host, window)
        manager.on_push("/a", "/b")
        assert manager._positions == {"/a": (0, 500)}
        host.run_all()
        assert window.scroll_calls == [(0, 0)]

    def test_save_on_pop(self):
        window = FakeScrollWindow()
        window.scrollY = 300
        host = QueueHostPort()
        manager = BrowserScrollManager(host, window)
        manager.on_pop("/b", "/a")
        assert manager._positions == {"/b": (0, 300)}

    def test_restore_on_pop(self):
        window = FakeScrollWindow()
        host = QueueHostPort()
        manager = BrowserScrollManager(host, window)
        manager._positions["/a"] = (0, 1200)
        manager.on_pop("/b", "/a")
        host.run_all()
        assert window.scroll_calls == [(0, 1200)]

    def test_top_on_first_visit(self):
        window = FakeScrollWindow()
        host = QueueHostPort()
        manager = BrowserScrollManager(host, window)
        manager.on_pop("/b", "/new")
        host.run_all()
        assert window.scroll_calls == [(0, 0)]

    def test_retry_until_tall_enough(self):
        window = FakeScrollWindow(scroll_height=800, inner_height=1000)
        host = QueueHostPort()
        manager = BrowserScrollManager(host, window)
        manager._positions["/a"] = (0, 2000)
        manager.on_pop("/b", "/a")
        host.run_next()
        assert window.scroll_calls == []
        window.document.documentElement.scrollHeight = 5000
        host.run_next()
        host.run_next()
        assert window.scroll_calls == [(0, 2000)]

    def test_give_up_clamps(self):
        window = FakeScrollWindow(scroll_height=800, inner_height=1000)
        host = QueueHostPort()
        manager = BrowserScrollManager(host, window)
        manager._positions["/a"] = (0, 2000)
        manager.on_pop("/b", "/a")
        host.run_all()
        assert window.scroll_calls == [(0, 0)]
        assert host.queue == []

    def test_short_page_no_retry(self):
        window = FakeScrollWindow(scroll_height=300, inner_height=1000)
        host = QueueHostPort()
        manager = BrowserScrollManager(host, window)
        manager.on_pop("/b", "/a")
        host.run_all()
        assert window.scroll_calls == [(0, 0)]
        assert host.queue == []
