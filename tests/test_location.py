from webcompy.router._change_event_handler import Location


class TestLocationInit:
    def test_init_hash_mode(self):
        loc = Location("hash", "")
        assert loc.__mode__ == "hash"

    def test_init_history_mode(self):
        loc = Location("history", "")
        assert loc.__mode__ == "history"

    def test_init_with_base_url(self):
        loc = Location("hash", "/app")
        assert loc._base_url == "app"

    def test_init_state_is_none(self):
        loc = Location("hash", "")
        assert loc._state is None


class TestLocationSetMode:
    def test_set_mode_changes_mode(self):
        loc = Location("hash", "")
        loc.set_mode("history")
        assert loc.__mode__ == "history"


class TestLocationSetPath:
    def test_set_path_history_mode(self):
        loc = Location("history", "")
        loc.__set_path__("/home", None)
        assert loc._value == "/home"

    def test_set_path_hash_mode_strips_hash(self):
        loc = Location("hash", "")
        loc.__set_path__("#/home", None)
        assert loc._value == "/home"

    def test_set_path_stores_state(self):
        loc = Location("hash", "")
        loc.__set_path__("/home", {"key": "val"})
        assert loc._state == {"key": "val"}


class TestLocationValue:
    def test_value_property(self):
        loc = Location("hash", "")
        assert loc.value == ""


class TestLocationRefreshPath:
    def test_refresh_path_no_browser(self):
        loc = Location("hash", "")
        loc._refresh_path()
        assert loc._value == ""

    def test_refresh_path_with_browser(self):

        import webcompy.router._change_event_handler as cem
        from tests.conftest import FakeBrowserModule
        from webcompy._browser import _modules

        fake = FakeBrowserModule()
        old_mod = _modules.browser
        old_cem = cem.browser
        _modules.browser = fake
        cem.browser = fake
        try:
            fake.window.location.pathname = "/test"
            fake.window.location.search = "?q=1"
            loc = Location("history", "")
            loc._refresh_path()
            assert loc._value == "/test?q=1"
        finally:
            _modules.browser = old_mod
            cem.browser = old_cem

    def test_refresh_path_hash_mode_with_browser(self):
        import webcompy.router._change_event_handler as cem
        from tests.conftest import FakeBrowserModule
        from webcompy._browser import _modules

        fake = FakeBrowserModule()
        old_mod = _modules.browser
        old_cem = cem.browser
        _modules.browser = fake
        cem.browser = fake
        try:
            fake.window.location.hash = "/about"
            loc = Location("hash", "")
            loc._refresh_path()
            assert loc._value == "/about"
        finally:
            _modules.browser = old_mod
            cem.browser = old_cem
