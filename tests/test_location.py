from tests.conftest import FakeBrowserModule, MockHistoryPort


class TestHistoryPortNavigate:
    def test_navigate_history_mode(self):
        hist = MockHistoryPort(mode="history")
        hist.navigate("/home", None)
        assert hist.value == "/home"

    def test_navigate_hash_mode_strips_hash(self):
        hist = MockHistoryPort(mode="hash")
        hist.navigate("#/home", None)
        assert hist.value == "/home"

    def test_navigate_stores_state(self):
        hist = MockHistoryPort(mode="history")
        hist.navigate("/home", {"key": "val"})
        assert hist._state == {"key": "val"}

    def test_navigate_state_is_none(self):
        hist = MockHistoryPort(mode="history")
        hist.navigate("/", None)
        assert hist._state is None


class TestBrowserHistoryPortRefreshPath:
    def test_refresh_path_history_mode(self, monkeypatch):
        fake = FakeBrowserModule()
        from webcompy.ports._browser import _raw
        from webcompy.ports._browser._history import BrowserHistoryPort

        monkeypatch.setattr("webcompy.ports._browser._history.ENVIRONMENT", "pyscript")
        old_browser = _raw.browser
        _raw.browser = fake
        try:
            fake.window.location.pathname = "/test"
            fake.window.location.search = "?q=1"
            fake.window.location.hash = ""
            fake.window.history._state = None
            hist = BrowserHistoryPort.__new__(BrowserHistoryPort)
            hist._browser = fake
            from webcompy.ports._history import HistoryPort

            HistoryPort.__init__(hist, "/test", mode="history")
            hist.refresh_from_window()
            assert hist.value == "/test?q=1"
        finally:
            _raw.browser = old_browser

    def test_refresh_path_hash_mode(self, monkeypatch):
        fake = FakeBrowserModule()
        from webcompy.ports._browser import _raw
        from webcompy.ports._browser._history import BrowserHistoryPort

        monkeypatch.setattr("webcompy.ports._browser._history.ENVIRONMENT", "pyscript")
        old_browser = _raw.browser
        _raw.browser = fake
        try:
            fake.window.location.pathname = "/"
            fake.window.location.search = ""
            fake.window.location.hash = "/about"
            fake.window.history._state = None
            hist = BrowserHistoryPort.__new__(BrowserHistoryPort)
            hist._browser = fake
            from webcompy.ports._history import HistoryPort

            HistoryPort.__init__(hist, "/", mode="hash")
            hist.refresh_from_window()
            assert hist.value == "//about"
        finally:
            _raw.browser = old_browser

    def test_refresh_path_reads_history_state(self, monkeypatch):
        fake = FakeBrowserModule()
        from webcompy.ports._browser import _raw
        from webcompy.ports._browser._history import BrowserHistoryPort

        monkeypatch.setattr("webcompy.ports._browser._history.ENVIRONMENT", "pyscript")
        old_browser = _raw.browser
        _raw.browser = fake
        try:
            fake.window.location.pathname = "/"
            fake.window.location.search = ""
            fake.window.location.hash = ""
            hist = BrowserHistoryPort.__new__(BrowserHistoryPort)
            hist._browser = fake
            from webcompy.ports._history import HistoryPort

            HistoryPort.__init__(hist, "/", mode="history")
            hist.refresh_from_window()
            assert hist._state is None
        finally:
            _raw.browser = old_browser


class TestMockHistoryPort:
    def test_init_hash_mode(self):
        hist = MockHistoryPort(mode="hash")
        assert hist.mode == "hash"

    def test_init_history_mode(self):
        hist = MockHistoryPort(mode="history")
        assert hist.mode == "history"

    def test_init_with_initial_path(self):
        hist = MockHistoryPort(mode="history", initial_path="/app")
        assert hist.value == "/app"

    def test_init_state_is_none(self):
        hist = MockHistoryPort(mode="history")
        assert hist.state is None

    def test_current_search_returns_empty(self):
        hist = MockHistoryPort(mode="history")
        assert hist.current_search() == ""

    def test_history_state_returns_state(self):
        hist = MockHistoryPort(mode="history")
        hist.navigate("/home", {"key": "val"})
        assert hist.history_state() == {"key": "val"}

    def test_refresh_from_window_is_noop(self):
        hist = MockHistoryPort(mode="history", initial_path="/keep")
        hist.refresh_from_window()
        assert hist.value == "/keep"
