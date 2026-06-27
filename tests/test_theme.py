from __future__ import annotations

import pytest

from webcompy.ui.theme._server import read_theme_from_cookie
from webcompy.ui.theme._theme import THEME_COOKIE_NAME, Theme


def test_read_theme_from_cookie_returns_system_when_no_headers() -> None:
    assert read_theme_from_cookie(None) is Theme.SYSTEM


def test_read_theme_from_cookie_returns_system_when_no_cookie() -> None:
    assert read_theme_from_cookie({}) is Theme.SYSTEM


def test_read_theme_from_cookie_parses_light() -> None:
    headers = {"cookie": f"{THEME_COOKIE_NAME}=light"}
    assert read_theme_from_cookie(headers) is Theme.LIGHT


def test_read_theme_from_cookie_parses_dark() -> None:
    headers = {"cookie": f"{THEME_COOKIE_NAME}=dark"}
    assert read_theme_from_cookie(headers) is Theme.DARK


def test_read_theme_from_cookie_parses_system() -> None:
    headers = {"cookie": f"{THEME_COOKIE_NAME}=system"}
    assert read_theme_from_cookie(headers) is Theme.SYSTEM


def test_read_theme_from_cookie_is_case_insensitive() -> None:
    headers = {"cookie": f"{THEME_COOKIE_NAME}=DARK"}
    assert read_theme_from_cookie(headers) is Theme.DARK


def test_read_theme_from_cookie_handles_invalid_value() -> None:
    headers = {"cookie": f"{THEME_COOKIE_NAME}=nonexistent"}
    assert read_theme_from_cookie(headers) is Theme.SYSTEM


def test_read_theme_from_cookie_ignores_other_cookies() -> None:
    headers = {"cookie": f"other=value; {THEME_COOKIE_NAME}=light"}
    assert read_theme_from_cookie(headers) is Theme.LIGHT


def test_read_theme_from_cookie_handles_list_headers() -> None:
    headers = [("Cookie", f"{THEME_COOKIE_NAME}=dark")]
    assert read_theme_from_cookie(headers) is Theme.DARK


def test_read_theme_from_cookie_handles_lowercase_header_keys() -> None:
    headers = {"Cookie": f"{THEME_COOKIE_NAME}=light"}
    assert read_theme_from_cookie(headers) is Theme.LIGHT


class FakeApp:
    def __init__(self) -> None:
        self.html_attrs: dict[str, str] = {}
        self._removed: list[str] = []

    def set_html_attr(self, key: str, value: object) -> None:
        self.html_attrs[key] = str(value)

    def remove_html_attr(self, key: str) -> None:
        self._removed.append(key)
        self.html_attrs.pop(key, None)


def test_theme_manager_set_updates_attr() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.SYSTEM)
    manager.set(Theme.DARK)
    assert app.html_attrs.get("data-theme") == "dark"


def test_theme_manager_system_removes_attr() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.DARK)
    assert app.html_attrs.get("data-theme") == "dark"
    manager.set(Theme.SYSTEM)
    assert "data-theme" not in app.html_attrs
    assert "data-theme" in app._removed


def test_theme_manager_initial_applies_attr() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    ThemeManager(app, app, Theme.LIGHT)
    assert app.html_attrs.get("data-theme") == "light"


def test_theme_manager_signal_reactive() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.LIGHT)
    captured: list[Theme] = []
    manager.signal.on_after_updating(lambda v: captured.append(v))
    manager.set(Theme.DARK)
    assert captured == [Theme.DARK]


def test_theme_manager_cycle() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.LIGHT)
    manager.cycle()
    assert manager.value is Theme.DARK
    manager.cycle()
    assert manager.value is Theme.SYSTEM
    manager.cycle()
    assert manager.value is Theme.LIGHT


def test_theme_manager_toggle_flips_light_dark() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.LIGHT)
    manager.toggle()
    assert manager.value is Theme.DARK
    manager.toggle()
    assert manager.value is Theme.LIGHT


def test_theme_manager_normalizes_string_initial() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, "DARK")
    assert manager.value is Theme.DARK


def test_use_theme_returns_signal_and_controller() -> None:
    from webcompy.di import DIScope
    from webcompy.ui._composables._theme import use_theme
    from webcompy.ui.theme._manager import ThemeManager
    from webcompy.ui.theme._theme import THEME_KEY

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.LIGHT)
    scope = DIScope()
    scope.provide(THEME_KEY, manager)
    with scope:
        signal, controller = use_theme()
        assert signal.value is Theme.LIGHT
        controller.set(Theme.DARK)
        assert signal.value is Theme.DARK


def test_use_theme_raises_without_manager() -> None:
    from webcompy.di import DIScope
    from webcompy.ui._composables._theme import use_theme

    scope = DIScope()
    with scope, pytest.raises(LookupError):
        use_theme()


def test_theme_controller_methods_delegate() -> None:
    from webcompy.ui._composables._theme_controller import ThemeController
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.LIGHT)
    controller = ThemeController(manager)
    controller.set(Theme.DARK)
    assert manager.value is Theme.DARK
    controller.toggle()
    assert manager.value is Theme.LIGHT
    controller.cycle()
    assert manager.value is Theme.DARK


def test_theme_manager_does_not_use_contextvar_for_set_html_attr() -> None:
    """ThemeManager must call the render context directly, not via the app's
    ContextVar-based set_html_attr, because the click handler runs outside the
    ContextVar's context and the ContextVar lookup would return None.
    """
    from webcompy.ui.theme._manager import ThemeManager

    class CountingApp:
        def __init__(self) -> None:
            self.set_calls = 0
            self.remove_calls = 0

        def set_html_attr(self, key: str, value: object) -> None:
            self.set_calls += 1

        def remove_html_attr(self, key: str) -> None:
            self.remove_calls += 1

    class RenderCtx:
        def __init__(self) -> None:
            self.set_calls = 0
            self.remove_calls = 0

        def set_html_attr(self, key: str, value: object) -> None:
            self.set_calls += 1

        def remove_html_attr(self, key: str) -> None:
            self.remove_calls += 1

    app = CountingApp()
    ctx = RenderCtx()
    manager = ThemeManager(app, ctx, Theme.SYSTEM)

    ctx_remove_calls_before = ctx.remove_calls
    ctx_set_calls_before = ctx.set_calls
    app_remove_calls_before = app.remove_calls
    app_set_calls_before = app.set_calls

    manager.set(Theme.DARK)
    assert ctx.set_calls - ctx_set_calls_before == 1
    assert app.set_calls - app_set_calls_before == 0

    manager.set(Theme.SYSTEM)
    assert ctx.remove_calls - ctx_remove_calls_before == 1
    assert app.remove_calls - app_remove_calls_before == 0
