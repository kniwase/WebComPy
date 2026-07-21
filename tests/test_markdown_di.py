from __future__ import annotations

from unittest.mock import MagicMock

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.app._render_context import BrowserRenderContext
from webcompy.di import inject
from webcompy.ports._keys import MARKDOWN_PORT_KEY
from webcompy.ports._markdown import MarkdownPort
from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy_server import configure_server_context


class _CustomMarkdownParser(MarkdownPort):
    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.invocations = 0

    def render(self, source: str) -> str:
        self.invocations += 1
        return f"<{self.tag}>{source}</{self.tag}>"


class TestServerRenderContextMarkdownPortDefault:
    def test_default_markdown_parser_provided(self) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app)
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            injected = ctx.di_scope.inject(MARKDOWN_PORT_KEY)
            assert isinstance(injected, DefaultMarkdownParser)
        finally:
            ctx.dispose()

    def test_default_markdown_parser_is_fresh_instance(self) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app)
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            injected = ctx.di_scope.inject(MARKDOWN_PORT_KEY)
            assert isinstance(injected, MarkdownPort)
            assert isinstance(injected, DefaultMarkdownParser)
        finally:
            ctx.dispose()


class TestServerRenderContextMarkdownPortOverride:
    def test_custom_parser_overrides_default_via_app_provide(self) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app)
        custom = _CustomMarkdownParser(tag="custom-md")
        app.provide(MARKDOWN_PORT_KEY, custom)
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            injected = ctx.di_scope.inject(MARKDOWN_PORT_KEY)
            assert injected is custom
            assert not isinstance(injected, DefaultMarkdownParser)
        finally:
            ctx.dispose()

    def test_custom_parser_renders_via_injected_port(self) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app)
        custom = _CustomMarkdownParser(tag="x-md")
        app.provide(MARKDOWN_PORT_KEY, custom)
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            injected = ctx.di_scope.inject(MARKDOWN_PORT_KEY)
            assert injected.render("# Title") == "<x-md># Title</x-md>"
            assert custom.invocations == 1
        finally:
            ctx.dispose()

    def test_custom_parser_overrides_default_when_called_before_context(self) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app)
        custom = _CustomMarkdownParser(tag="early-md")
        app.provide(MARKDOWN_PORT_KEY, custom)
        assert len(app._deferred_ops) == 1
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            injected = ctx.di_scope.inject(MARKDOWN_PORT_KEY)
            assert injected is custom
        finally:
            ctx.dispose()


class TestServerRenderContextMarkdownPortGlobalInject:
    def test_global_inject_returns_default_while_context_active(self) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app)
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            injected = inject(MARKDOWN_PORT_KEY)
            assert isinstance(injected, DefaultMarkdownParser)
        finally:
            ctx.dispose()

    def test_global_inject_returns_custom_when_overridden(self) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app)
        custom = _CustomMarkdownParser(tag="global-md")
        app.provide(MARKDOWN_PORT_KEY, custom)
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            injected = inject(MARKDOWN_PORT_KEY)
            assert injected is custom
        finally:
            ctx.dispose()


_BROWSER_PORT_STUB_MODULES: list[tuple[str, str]] = [
    ("webcompy.ports._browser._async_scheduler", "BrowserAsyncSchedulerPort"),
    ("webcompy.ports._browser._cookie", "BrowserCookiePort"),
    ("webcompy.ports._browser._dom", "BrowserDOMPort"),
    ("webcompy.ports._browser._fetch", "BrowserFetchPort"),
    ("webcompy.ports._browser._ffi", "BrowserFFIPort"),
    ("webcompy.ports._browser._history", "BrowserHistoryPort"),
    ("webcompy.ports._browser._host", "BrowserHostPort"),
    ("webcompy.ports._browser._media_query", "BrowserMediaQueryPort"),
    ("webcompy.ports._browser._resource", "BrowserResourcePort"),
]


def _stub_browser_ports(monkeypatch) -> None:
    for mod_name, cls_name in _BROWSER_PORT_STUB_MODULES:
        monkeypatch.setattr(f"{mod_name}.{cls_name}", MagicMock())


class TestBrowserRenderContextMarkdownPortDefault:
    def test_default_markdown_parser_provided(self, monkeypatch) -> None:
        _stub_browser_ports(monkeypatch)
        monkeypatch.setattr(
            BrowserRenderContext,
            "_load_hydration_payload",
            lambda self: None,
        )

        captured: dict[str, object] = {}

        def fake_provide(key, value):
            if key is MARKDOWN_PORT_KEY:
                captured["port"] = value

        di_scope = MagicMock()
        di_scope.provide.side_effect = fake_provide

        instance = BrowserRenderContext.__new__(BrowserRenderContext)
        instance._di_scope = di_scope
        instance._config = WebComPyAppConfig()
        instance._router = None

        instance._register_ports()

        assert "port" in captured
        assert isinstance(captured["port"], DefaultMarkdownParser)

    def test_default_markdown_parser_is_markdown_port_subclass(self, monkeypatch) -> None:
        _stub_browser_ports(monkeypatch)
        monkeypatch.setattr(
            BrowserRenderContext,
            "_load_hydration_payload",
            lambda self: None,
        )

        provided: dict[object, object] = {}

        def fake_provide(key, value):
            provided[key] = value

        di_scope = MagicMock()
        di_scope.provide.side_effect = fake_provide

        instance = BrowserRenderContext.__new__(BrowserRenderContext)
        instance._di_scope = di_scope
        instance._config = WebComPyAppConfig()
        instance._router = None

        instance._register_ports()

        assert MARKDOWN_PORT_KEY in provided
        port = provided[MARKDOWN_PORT_KEY]
        assert isinstance(port, MarkdownPort)
        assert isinstance(port, DefaultMarkdownParser)

    def test_default_markdown_parser_registered_before_hydration_load(self, monkeypatch) -> None:
        _stub_browser_ports(monkeypatch)

        events: list[tuple[str, object | None]] = []

        def fake_provide(key, value):
            events.append(("provide", key))

        di_scope = MagicMock()
        di_scope.provide.side_effect = fake_provide

        instance = BrowserRenderContext.__new__(BrowserRenderContext)
        instance._di_scope = di_scope
        instance._config = WebComPyAppConfig()
        instance._router = None

        def fake_hydration() -> None:
            events.append(("hydration", None))

        monkeypatch.setattr(instance, "_load_hydration_payload", fake_hydration)

        instance._register_ports()

        markdown_index = next(
            i for i, (kind, key) in enumerate(events) if kind == "provide" and key is MARKDOWN_PORT_KEY
        )
        hydration_index = next(i for i, (kind, _key) in enumerate(events) if kind == "hydration")
        assert markdown_index < hydration_index
