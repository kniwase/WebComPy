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


def test_dark_tokens_match_legacy_tokens_dark_css() -> None:
    """The Python DARK_TOKENS dict must match the values that were
    previously in tokens-dark.css. If a token is added to one, it must
    be added to the other.
    """
    from webcompy.ui.theme._tokens import DARK_TOKENS, LIGHT_TOKENS

    expected = {
        "--color-bg": "#0d1117",
        "--color-bg-elevated": "#161b22",
        "--color-bg-code": "#161b22",
        "--color-bg-card": "#161b22",
        "--color-fg": "#e6edf3",
        "--color-fg-muted": "#8d96a0",
        "--color-fg-subtle": "#6e7681",
        "--color-link": "#4493f8",
        "--color-link-hover": "#58a6ff",
        "--color-accent": "#4493f8",
        "--color-border": "#30363d",
        "--color-border-muted": "#21262d",
        "--color-success": "#3fb950",
        "--color-danger": "#f85149",
        "--color-warning": "#d29922",
        "--shadow-sm": "0 1px 0 rgba(0, 0, 0, 0.4)",
        "--shadow-md": "0 3px 6px rgba(0, 0, 0, 0.45)",
        "--tok-kw": "#ff7b72",
        "--tok-str": "#a5d6ff",
        "--tok-num": "#79c0ff",
        "--tok-comment": "#8b949e",
        "--tok-fn": "#d2a8ff",
        "--tok-builtin": "#ffa657",
        "--tok-decorator": "#ffa657",
        "--tok-op": "#e6edf3",
        "--tok-punct": "#e6edf3",
        "--tok-ident": "#e6edf3",
    }
    assert expected == DARK_TOKENS

    light_expected = {
        "--color-bg": "#ffffff",
        "--color-bg-elevated": "#f6f8fa",
        "--color-bg-code": "#f6f8fa",
        "--color-bg-card": "#ffffff",
        "--color-fg": "#1f2328",
        "--color-fg-muted": "#57606a",
        "--color-fg-subtle": "#6e7781",
        "--color-link": "#0969da",
        "--color-link-hover": "#0550ae",
        "--color-accent": "#0969da",
        "--color-border": "#d0d7de",
        "--color-border-muted": "#d8dee4",
        "--color-success": "#1a7f37",
        "--color-danger": "#d1242f",
        "--color-warning": "#9a6700",
        "--shadow-sm": "0 1px 0 rgba(31, 35, 40, 0.04)",
        "--shadow-md": "0 3px 6px rgba(140, 149, 159, 0.15)",
        "--tok-kw": "#cf222e",
        "--tok-str": "#0a3069",
        "--tok-num": "#0550ae",
        "--tok-comment": "#6e7781",
        "--tok-fn": "#8250df",
        "--tok-builtin": "#953800",
        "--tok-decorator": "#953800",
        "--tok-op": "#1f2328",
        "--tok-punct": "#1f2328",
        "--tok-ident": "#1f2328",
    }
    assert light_expected == LIGHT_TOKENS


def test_read_theme_from_cookie_handles_lowercase_header_keys() -> None:
    headers = {"Cookie": f"{THEME_COOKIE_NAME}=light"}
    assert read_theme_from_cookie(headers) is Theme.LIGHT


class FakeApp:
    def __init__(self) -> None:
        self.html_attrs: dict[str, str] = {}
        self._removed: list[str] = []
        self.styles: list[object] = []

    def set_html_attr(self, key: str, value: object) -> None:
        self.html_attrs[key] = str(value)

    def remove_html_attr(self, key: str) -> None:
        self._removed.append(key)
        self.html_attrs.pop(key, None)

    def append_style(self, content: object) -> None:
        self.styles.append(content)


def test_theme_manager_register_reactive_style_after_root() -> None:
    """ThemeManager.__init__ does NOT register the style directly. The
    render context calls ``register_style()`` AFTER the AppDocumentRoot
    is created, because the head element is part of the root.
    """
    from webcompy.ui.theme._manager import ThemeManager

    class FakeAppWithStyles:
        def __init__(self) -> None:
            self.styles: list[object] = []

        def append_style(self, content: object) -> None:
            self.styles.append(content)

    app = FakeAppWithStyles()
    manager = ThemeManager(app, app, Theme.SYSTEM)
    assert len(app.styles) == 0
    manager.register_style()
    assert len(app.styles) == 1


def test_theme_manager_light_emits_empty_css() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    class FakeApp:
        def __init__(self) -> None:
            self.content = None

        def append_style(self, content: object) -> None:
            self.content = content

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.LIGHT)
    assert manager._build_theme_css() == ""


def test_theme_manager_dark_emits_root_with_dark_tokens() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.DARK)
    css = manager._build_theme_css()
    assert css.startswith(":root {")
    assert "--color-bg: #0d1117" in css
    assert "--color-fg: #e6edf3" in css


def test_theme_manager_system_emits_prefers_color_scheme_dark() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.SYSTEM)
    css = manager._build_theme_css()
    assert "@media (prefers-color-scheme: dark)" in css
    assert ":root" in css
    assert "--color-bg: #0d1117" in css


def test_theme_manager_set_updates_reactive_computed() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    class FakeApp:
        def __init__(self) -> None:
            self.content = None

        def append_style(self, content: object) -> None:
            self.content = content

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.LIGHT)
    manager.set(Theme.DARK)
    css = manager._build_theme_css()
    assert "--color-bg: #0d1117" in css


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
    from webcompy.ui.theme import use_theme
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
    from webcompy.ui.theme import use_theme

    scope = DIScope()
    with scope, pytest.raises(LookupError):
        use_theme()


def test_theme_controller_methods_delegate() -> None:
    from webcompy.ui.composables._theme_controller import ThemeController
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


class _FakeMediaQueryPort:
    def __init__(self, prefers_dark: bool) -> None:
        self._prefers_dark = prefers_dark
        self.calls = 0

    def prefers_dark(self) -> bool:
        self.calls += 1
        return self._prefers_dark


def _mocked_media_query_scope(
    prefers_dark: bool,
) -> tuple[_FakeMediaQueryPort, object]:
    from webcompy.di import DIScope
    from webcompy.ports._keys import MEDIA_QUERY_PORT_KEY

    port = _FakeMediaQueryPort(prefers_dark)
    scope = DIScope()
    scope.provide(MEDIA_QUERY_PORT_KEY, port)
    return port, scope


def test_system_preferred_theme_returns_dark_when_port_prefers_dark() -> None:
    from webcompy.ui.theme._manager import _system_preferred_theme

    port, scope = _mocked_media_query_scope(prefers_dark=True)
    with scope:
        result = _system_preferred_theme()
    assert result is Theme.DARK
    assert port.calls == 1


def test_system_preferred_theme_returns_light_when_port_prefers_light() -> None:
    from webcompy.ui.theme._manager import _system_preferred_theme

    _port, scope = _mocked_media_query_scope(prefers_dark=False)
    with scope:
        result = _system_preferred_theme()
    assert result is Theme.LIGHT


def test_system_preferred_theme_defaults_to_light_when_no_port() -> None:
    from webcompy.di import DIScope
    from webcompy.ui.theme._manager import _system_preferred_theme

    scope = DIScope()
    with scope:
        result = _system_preferred_theme()
    assert result is Theme.LIGHT


def test_toggle_from_system_with_dark_pref_goes_to_light() -> None:
    from webcompy.ui.theme._manager import ThemeManager
    from webcompy.ui.theme._theme import THEME_KEY

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.SYSTEM)
    _port, scope = _mocked_media_query_scope(prefers_dark=True)
    scope.provide(THEME_KEY, manager)
    with scope:
        manager.toggle()
    assert manager.value is Theme.LIGHT


def test_toggle_from_system_with_light_pref_goes_to_dark() -> None:
    from webcompy.ui.theme._manager import ThemeManager
    from webcompy.ui.theme._theme import THEME_KEY

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.SYSTEM)
    _port, scope = _mocked_media_query_scope(prefers_dark=False)
    scope.provide(THEME_KEY, manager)
    with scope:
        manager.toggle()
    assert manager.value is Theme.DARK


def test_toggle_from_system_does_not_stay_on_system() -> None:
    from webcompy.ui.theme._manager import ThemeManager
    from webcompy.ui.theme._theme import THEME_KEY

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.SYSTEM)
    _port, scope = _mocked_media_query_scope(prefers_dark=False)
    scope.provide(THEME_KEY, manager)
    with scope:
        manager.toggle()
    assert manager.value is not Theme.SYSTEM
