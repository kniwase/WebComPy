from __future__ import annotations

from webcompy_server.ports import ServerHostPort
from webcompy_testing import FakeBrowserHostPort


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
