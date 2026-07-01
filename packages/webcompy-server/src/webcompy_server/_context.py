from __future__ import annotations

from typing import Any

from webcompy.app._render_context import RenderContext
from webcompy.ports._keys import (
    COOKIE_PORT_KEY,
    DOM_PORT_KEY,
    FETCH_PORT_KEY,
    FFI_PORT_KEY,
    HISTORY_PORT_KEY,
    HOST_PORT_KEY,
    MEDIA_QUERY_PORT_KEY,
)
from webcompy_server._html import generate_html
from webcompy_server.ports._cookie import ServerCookiePort
from webcompy_server.ports._dom import ServerDOMPort
from webcompy_server.ports._fetch import ServerFetchPort
from webcompy_server.ports._ffi import ServerFFIPort
from webcompy_server.ports._history import ServerHistoryPort
from webcompy_server.ports._host import ServerHostPort
from webcompy_server.ports._media_query import ServerMediaQueryPort


class ServerRenderContext(RenderContext):
    def _register_ports(self) -> None:
        router_mode = self._router.__mode__ if self._router else "history"
        self._di_scope.provide(COOKIE_PORT_KEY, ServerCookiePort(self._cookie_header))
        self._di_scope.provide(DOM_PORT_KEY, ServerDOMPort())
        self._di_scope.provide(FETCH_PORT_KEY, ServerFetchPort())
        self._di_scope.provide(FFI_PORT_KEY, ServerFFIPort())
        self._di_scope.provide(HISTORY_PORT_KEY, ServerHistoryPort(mode=router_mode))
        self._di_scope.provide(HOST_PORT_KEY, ServerHostPort())
        self._di_scope.provide(MEDIA_QUERY_PORT_KEY, ServerMediaQueryPort())

    async def render_html(self, **kwargs: Any) -> str:
        return await generate_html(self, **kwargs)
