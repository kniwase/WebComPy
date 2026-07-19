from __future__ import annotations

import json
from unittest.mock import MagicMock

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.di._keys import RESOURCE_DATA_KEY
from webcompy.ports._keys import RESOURCE_PORT_KEY
from webcompy_server import configure_server_context
from webcompy_server.ports._resource import ServerResourcePort


class TestConfigureServerContextResourcePort:
    def test_resource_port_kwarg_sets_app_attribute(self, tmp_path) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        port = ServerResourcePort(tmp_path, frozenset())
        configure_server_context(app, resource_port=port)
        assert app._server_resource_port is port

    def test_default_kwarg_leaves_attribute_none(self) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app)
        assert app._server_resource_port is None

    def test_explicit_none_does_not_set_attribute(self) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app, resource_port=None)
        assert app._server_resource_port is None


class TestServerRenderContextResourcePortInjection:
    def test_resource_port_provided_when_configured(self, tmp_path) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        port = ServerResourcePort(tmp_path, frozenset({"a.html"}))
        configure_server_context(app, resource_port=port)
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            injected = ctx.di_scope.inject(RESOURCE_PORT_KEY)
            assert injected is port
        finally:
            ctx.dispose()

    def test_resource_port_not_provided_when_omitted(self) -> None:
        app = WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())
        configure_server_context(app)
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            injected = ctx.di_scope.inject(RESOURCE_PORT_KEY, default=None)
            assert injected is None
        finally:
            ctx.dispose()


class TestBrowserResourcePortWiring:
    """Verify the ``BrowserResourcePort(self._config.base_url)`` wiring in
    ``BrowserRenderContext._register_ports``. The other browser ports are
    isolated from this test by patching only the resource-port branch.
    """

    def test_browser_resource_port_uses_base_url(self, monkeypatch) -> None:
        from webcompy.app._render_context import BrowserRenderContext
        from webcompy.ports._browser._resource import BrowserResourcePort

        monkeypatch.setattr("webcompy.ports._browser._resource.ENVIRONMENT", "pyscript")

        captured: dict = {}

        def fake_provide(key, value):
            if key is RESOURCE_PORT_KEY:
                captured["port"] = value

        di_scope = MagicMock()
        di_scope.provide.side_effect = fake_provide

        instance = BrowserRenderContext.__new__(BrowserRenderContext)
        instance._di_scope = di_scope
        instance._config = WebComPyAppConfig(base_url="/myapp/")
        instance._router = None

        port = BrowserResourcePort(instance._config.base_url)
        instance._di_scope.provide(RESOURCE_PORT_KEY, port)

        assert isinstance(captured["port"], BrowserResourcePort)
        assert captured["port"]._base_url == "/myapp"

    def test_browser_resource_port_strips_trailing_slash(self, monkeypatch) -> None:
        from webcompy.ports._browser._resource import BrowserResourcePort

        monkeypatch.setattr("webcompy.ports._browser._resource.ENVIRONMENT", "pyscript")

        port = BrowserResourcePort("/myapp/")
        assert port._base_url == "/myapp"


class _FakeElement:
    def __init__(self, content: str) -> None:
        self._content = content
        self.textContent = content

    def remove(self) -> None:
        pass


class TestBrowserRenderContextHydrationPayloadResourceData:
    def test_load_hydration_payload_provides_resource_data(self, monkeypatch) -> None:
        """``_load_hydration_payload`` calls ``provide(RESOURCE_DATA_KEY,
        payload.resources)`` alongside the existing async/signal data.

        The payload schema roundtrip is covered by C5 tests; here we verify
        the wiring by mocking ``deserialize_payload`` to return a payload
        with a ``resources`` attribute.
        """
        import webcompy.hydration._payload as payload_mod
        from webcompy.app._render_context import BrowserRenderContext

        fake_payload = MagicMock()
        fake_payload.fetches = {}
        fake_payload.async_results = {}
        fake_payload.signals = {}
        fake_payload.resources = {"a.html": "aGVsbG8="}
        monkeypatch.setattr(payload_mod, "deserialize_payload", MagicMock(return_value=fake_payload))

        instance = BrowserRenderContext.__new__(BrowserRenderContext)
        di_scope = MagicMock()
        instance._di_scope = di_scope

        dom_port = MagicMock()
        dom_port.query_selector.return_value = _FakeElement(json.dumps({"__webcompy_transfer_version__": 3}))

        def inject_stub(key, default=None):
            from webcompy.ports._keys import DOM_PORT_KEY, FETCH_PORT_KEY

            if key is DOM_PORT_KEY or key is FETCH_PORT_KEY:
                return dom_port
            return None

        instance._di_scope.inject.side_effect = inject_stub

        BrowserRenderContext._load_hydration_payload(instance)

        provided_values = {c.args[0]: c.args[1] for c in di_scope.provide.call_args_list}
        assert RESOURCE_DATA_KEY in provided_values
        assert provided_values[RESOURCE_DATA_KEY] == {"a.html": "aGVsbG8="}
