from __future__ import annotations

import pytest

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.ports._keys import COOKIE_PORT_KEY
from webcompy.ports._server._cookie import ServerCookiePort


@pytest.fixture
def app() -> WebComPyApp:
    return WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())


class TestRenderContextCookieHeader:
    def test_server_cookie_port_is_populated_from_header(self, app: WebComPyApp) -> None:
        """ServerCookiePort in the DI scope MUST be initialized with the
        request's ``cookie`` header so server-side code that calls
        ``inject(COOKIE_PORT_KEY).get('webcompy-theme')`` sees the same
        value that ``read_theme_from_cookie`` parsed for ``initial_theme``.

        Regression test for PR #178 fourth-round review."""
        ctx = app.create_render_context(
            "/",
            initial_theme=None,
            cookie_header="webcompy-theme=dark; other=value",
        )
        try:
            port = ctx.di_scope.inject(COOKIE_PORT_KEY)
            assert isinstance(port, ServerCookiePort)
            assert port.get("webcompy-theme") == "dark"
            assert port.get("other") == "value"
        finally:
            ctx.dispose()

    def test_missing_cookie_header_leaves_port_empty(self, app: WebComPyApp) -> None:
        ctx = app.create_render_context("/", initial_theme=None)
        try:
            port = ctx.di_scope.inject(COOKIE_PORT_KEY)
            assert isinstance(port, ServerCookiePort)
            assert port.get("webcompy-theme") is None
        finally:
            ctx.dispose()

    def test_empty_cookie_header_leaves_port_empty(self, app: WebComPyApp) -> None:
        ctx = app.create_render_context("/", initial_theme=None, cookie_header="")
        try:
            port = ctx.di_scope.inject(COOKIE_PORT_KEY)
            assert isinstance(port, ServerCookiePort)
            assert port.get("webcompy-theme") is None
        finally:
            ctx.dispose()
