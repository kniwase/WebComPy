from __future__ import annotations

from typing import Any

from webcompy_server.ports import ServerHostPort
from webcompy_testing import FakeBrowserDOMPort, FakeBrowserHostPort


class TestServerHostPort:
    def test_add_window_event_listener_returns_cleanup(self):
        host = ServerHostPort()
        remove = host.add_window_event_listener("resize", lambda _ev: None)
        assert callable(remove)
        remove()


class TestFakeBrowserHostPort:
    def test_add_window_event_listener_returns_cleanup(self):
        host = FakeBrowserHostPort()
        remove = host.add_window_event_listener("resize", lambda _ev: None)
        assert callable(remove)
        remove()

    def test_dispatch_window_event_invokes_registered_handlers(self):
        host = FakeBrowserHostPort()
        calls: list[Any] = []
        host.add_window_event_listener("resize", lambda ev: calls.append(ev))
        host.dispatch_window_event("resize", {"innerWidth": 800})
        assert calls == [{"innerWidth": 800}]

    def test_dispatch_window_event_skips_handler_removed_during_dispatch(self):
        host = FakeBrowserHostPort()
        calls: list[str] = []
        remove_other = None

        def remover(_ev: Any) -> None:
            assert remove_other is not None
            remove_other()
            calls.append("remover")

        host.add_window_event_listener("resize", remover)
        remove_other = host.add_window_event_listener("resize", lambda _ev: calls.append("removed"))
        host.add_window_event_listener("resize", lambda _ev: calls.append("kept"))
        host.dispatch_window_event("resize", None)
        assert calls == ["remover", "kept"]


class TestFakeBrowserDOMPort:
    def test_dispatch_document_event_invokes_registered_handlers(self):
        dom = FakeBrowserDOMPort()
        calls: list[Any] = []
        dom.add_document_event_listener("visibilitychange", lambda ev: calls.append(ev))
        dom.dispatch_document_event("visibilitychange", {"state": "hidden"})
        assert calls == [{"state": "hidden"}]

    def test_dispatch_document_event_skips_handler_removed_during_dispatch(self):
        dom = FakeBrowserDOMPort()
        calls: list[str] = []
        remove_other = None

        def remover(_ev: Any) -> None:
            assert remove_other is not None
            remove_other()
            calls.append("remover")

        dom.add_document_event_listener("visibilitychange", remover)
        remove_other = dom.add_document_event_listener("visibilitychange", lambda _ev: calls.append("removed"))
        dom.add_document_event_listener("visibilitychange", lambda _ev: calls.append("kept"))
        dom.dispatch_document_event("visibilitychange", None)
        assert calls == ["remover", "kept"]
