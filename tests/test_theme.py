from __future__ import annotations

import warnings

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
        "--color-accent": "#1f6feb",
        "--color-on-accent": "#ffffff",
        "--color-border": "#30363d",
        "--color-border-muted": "#21262d",
        "--color-success": "#3fb950",
        "--color-danger": "#f85149",
        "--color-warning": "#d29922",
        "--shadow-sm": "0 1px 0 rgba(0, 0, 0, 0.4)",
        "--shadow-md": "0 3px 6px rgba(0, 0, 0, 0.45)",
        "--shadow-lg": "0 8px 24px rgba(0, 0, 0, 0.6)",
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
        "--color-on-accent": "#ffffff",
        "--color-border": "#d0d7de",
        "--color-border-muted": "#d8dee4",
        "--color-success": "#1a7f37",
        "--color-danger": "#d1242f",
        "--color-warning": "#9a6700",
        "--shadow-sm": "0 1px 0 rgba(31, 35, 40, 0.04)",
        "--shadow-md": "0 3px 6px rgba(140, 149, 159, 0.15)",
        "--shadow-lg": "0 8px 24px rgba(140, 149, 159, 0.2)",
        "--tok-kw": "#cf222e",
        "--tok-str": "#0a3069",
        "--tok-num": "#0550ae",
        "--tok-comment": "#59636e",
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


def test_theme_manager_light_emits_color_scheme_light() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    class FakeApp:
        def __init__(self) -> None:
            self.content = None

        def append_style(self, content: object) -> None:
            self.content = content

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.LIGHT)
    css = manager._build_theme_css()
    assert css.startswith(":root {")
    assert "color-scheme: light;" in css
    assert "--color-bg: #0d1117" not in css


def test_theme_manager_dark_emits_root_with_dark_tokens() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.DARK)
    css = manager._build_theme_css()
    assert css.startswith(":root {")
    assert "color-scheme: dark;" in css
    assert "--color-bg: #0d1117" in css
    assert "--color-fg: #e6edf3" in css


def test_theme_manager_system_emits_prefers_color_scheme_dark() -> None:
    from webcompy.ui.theme._manager import ThemeManager

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.SYSTEM)
    css = manager._build_theme_css()
    assert "@media (prefers-color-scheme: dark)" in css
    assert ":root" in css
    assert "color-scheme: dark;" in css
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


def test_use_theme_does_not_emit_userwarning() -> None:
    from webcompy.di import DIScope
    from webcompy.ui.theme import use_theme
    from webcompy.ui.theme._manager import ThemeManager
    from webcompy.ui.theme._theme import THEME_KEY

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.LIGHT)
    scope = DIScope()
    scope.provide(THEME_KEY, manager)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with scope:
            signal, controller = use_theme()
    userwarnings = [x for x in w if issubclass(x.category, UserWarning)]
    assert len(userwarnings) == 0
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

    def prefers_reduced_motion(self) -> bool:
        return False


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


class _AppWithConfig(FakeApp):
    def __init__(self, theme: dict | None) -> None:
        super().__init__()
        from webcompy.app._config import WebComPyAppConfig

        self._config = WebComPyAppConfig(theme=theme)


def test_set_writes_cookie_when_persist_enabled_by_default(monkeypatch) -> None:
    from webcompy.di import DIScope
    from webcompy.ports._keys import COOKIE_PORT_KEY
    from webcompy.ui.theme._manager import ThemeManager
    from webcompy.ui.theme._theme import THEME_KEY

    calls: list[tuple[str, str]] = []

    class _CookiePort:
        def set(self, name: str, value: str, **kwargs: object) -> None:
            calls.append((name, value))

        def delete(self, name: str, **kwargs: object) -> None:
            calls.append((name, ""))

    app = _AppWithConfig(theme=None)
    manager = ThemeManager(app, app, Theme.SYSTEM)
    scope = DIScope()
    scope.provide(THEME_KEY, manager)
    scope.provide(COOKIE_PORT_KEY, _CookiePort())
    with scope:
        manager.set(Theme.DARK)
    assert (THEME_COOKIE_NAME, "dark") in calls


def test_set_skips_cookie_when_persist_false(monkeypatch) -> None:
    from webcompy.di import DIScope
    from webcompy.ports._keys import COOKIE_PORT_KEY
    from webcompy.ui.theme._manager import ThemeManager
    from webcompy.ui.theme._theme import THEME_KEY

    calls: list[tuple[str, str]] = []

    class _CookiePort:
        def set(self, name: str, value: str, **kwargs: object) -> None:
            calls.append((name, value))

        def delete(self, name: str, **kwargs: object) -> None:
            calls.append((name, ""))

    app = _AppWithConfig(theme={"default": "light", "persist": False})
    manager = ThemeManager(app, app, Theme.LIGHT)
    scope = DIScope()
    scope.provide(THEME_KEY, manager)
    scope.provide(COOKIE_PORT_KEY, _CookiePort())
    with scope:
        manager.set(Theme.DARK)
    assert calls == []


def _srgb_channel(val: int) -> float:
    c = val / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    return 0.2126 * _srgb_channel(r) + 0.7152 * _srgb_channel(g) + 0.0722 * _srgb_channel(b)


def _contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    l1 = _relative_luminance(fg_hex)
    l2 = _relative_luminance(bg_hex)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("token_set_name", ["LIGHT_TOKENS", "DARK_TOKENS"])
def test_theme_tokens_meet_wcag_aa_contrast(token_set_name: str) -> None:
    from webcompy.ui.theme import _tokens

    tokens = getattr(_tokens, token_set_name)
    pairs = [
        ("--color-fg", "--color-bg"),
        ("--color-fg", "--color-bg-card"),
        ("--color-fg", "--color-bg-elevated"),
        ("--color-fg-muted", "--color-bg"),
        ("--color-fg-muted", "--color-bg-card"),
        ("--color-fg-muted", "--color-bg-elevated"),
        ("--color-link", "--color-bg"),
        ("--color-link", "--color-bg-card"),
        ("--color-on-accent", "--color-accent"),
        ("--tok-comment", "--color-bg-code"),
        ("--tok-kw", "--color-bg-code"),
        ("--tok-str", "--color-bg-code"),
        ("--tok-num", "--color-bg-code"),
        ("--tok-fn", "--color-bg-code"),
        ("--tok-builtin", "--color-bg-code"),
        ("--tok-decorator", "--color-bg-code"),
        ("--tok-op", "--color-bg-code"),
        ("--tok-punct", "--color-bg-code"),
        ("--tok-ident", "--color-bg-code"),
    ]
    for fg_key, bg_key in pairs:
        ratio = _contrast_ratio(tokens[fg_key], tokens[bg_key])
        assert ratio >= 4.5, f"{token_set_name} {fg_key} on {bg_key} contrast {ratio:.2f}:1 < 4.5:1"


def test_tokens_css_matches_python_light_and_dark_token_keys() -> None:
    import re

    from webcompy.ui._styles import get_styles_file
    from webcompy.ui.theme._tokens import DARK_TOKENS, LIGHT_TOKENS

    raw = get_styles_file("tokens.css")
    assert raw is not None
    css = raw.decode("utf-8")
    css_pairs = dict(re.findall(r"(--(?:color|shadow|tok)-[a-z0-9-]+):\s*([^;]+);", css))
    assert set(css_pairs) == set(LIGHT_TOKENS)
    assert set(LIGHT_TOKENS) == set(DARK_TOKENS)
    for key, val in LIGHT_TOKENS.items():
        assert css_pairs[key].strip() == val, f"Mismatch for {key}: css={css_pairs[key]!r} vs py={val!r}"


def test_detect_prerendered_theme_parses_dynamic_style() -> None:
    from webcompy.app._render_context import _detect_prerendered_theme

    assert (
        _detect_prerendered_theme("@media (prefers-color-scheme: dark) { :root { --color-bg: #0d1117; } }")
        is Theme.SYSTEM
    )
    assert (
        _detect_prerendered_theme(":root {\n  color-scheme: dark;\n  --color-bg: #0d1117 !important;\n}") is Theme.DARK
    )
    assert _detect_prerendered_theme(":root {\n  color-scheme: light;\n}") is Theme.LIGHT
    assert _detect_prerendered_theme("") is Theme.LIGHT
    assert _detect_prerendered_theme("body { margin: 0; }") is None


def test_apply_without_persist_updates_signal_without_touching_cookie() -> None:
    from webcompy.di import DIScope
    from webcompy.ports._keys import COOKIE_PORT_KEY
    from webcompy.ui.theme._manager import ThemeManager
    from webcompy.ui.theme._theme import THEME_KEY

    calls: list[tuple[str, str]] = []

    class _CookiePort:
        def set(self, name: str, value: str, **kwargs: object) -> None:
            calls.append((name, value))

        def delete(self, name: str, **kwargs: object) -> None:
            calls.append((name, ""))

    app = FakeApp()
    manager = ThemeManager(app, app, Theme.SYSTEM)
    scope = DIScope()
    scope.provide(THEME_KEY, manager)
    scope.provide(COOKIE_PORT_KEY, _CookiePort())
    with scope:
        manager._apply_without_persist(Theme.DARK)
    assert manager.value is Theme.DARK
    assert calls == []
