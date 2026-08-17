from __future__ import annotations

from typing import Any

from webcompy.app._render_context import RenderContext
from webcompy.ports._keys import (
    ASYNC_SCHEDULER_PORT_KEY,
    COOKIE_PORT_KEY,
    CUSTOM_ELEMENT_PORT_KEY,
    DOM_PORT_KEY,
    EVENT_SOURCE_PORT_KEY,
    FETCH_PORT_KEY,
    FFI_PORT_KEY,
    HISTORY_PORT_KEY,
    HOST_PORT_KEY,
    MARKDOWN_PORT_KEY,
    MEDIA_QUERY_PORT_KEY,
    RESOURCE_PORT_KEY,
    TRANSITION_PORT_KEY,
    WEBSOCKET_PORT_KEY,
)
from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy_server._html import generate_html
from webcompy_server.ports._async_scheduler import ServerAsyncSchedulerPort
from webcompy_server.ports._cookie import ServerCookiePort
from webcompy_server.ports._custom_element import ServerCustomElementPort
from webcompy_server.ports._dom import ServerDOMPort
from webcompy_server.ports._event_source import ServerEventSourcePort
from webcompy_server.ports._fetch import ServerFetchPort
from webcompy_server.ports._ffi import ServerFFIPort
from webcompy_server.ports._history import ServerHistoryPort
from webcompy_server.ports._host import ServerHostPort
from webcompy_server.ports._media_query import ServerMediaQueryPort
from webcompy_server.ports._transition import ServerTransitionPort
from webcompy_server.ports._websocket import ServerWebSocketPort


class ServerRenderContext(RenderContext):
    def _register_ports(self) -> None:
        assert self._di_scope is not None
        router_mode = self._router.__mode__ if self._router else "history"
        override_scheduler = getattr(self._app, "_test_async_scheduler_port", None)
        if override_scheduler is not None:
            self._di_scope.provide(ASYNC_SCHEDULER_PORT_KEY, override_scheduler)
        else:
            self._di_scope.provide(ASYNC_SCHEDULER_PORT_KEY, ServerAsyncSchedulerPort())
        self._di_scope.provide(COOKIE_PORT_KEY, ServerCookiePort(self._cookie_header))
        self._di_scope.provide(CUSTOM_ELEMENT_PORT_KEY, ServerCustomElementPort())
        self._di_scope.provide(DOM_PORT_KEY, ServerDOMPort())
        self._di_scope.provide(EVENT_SOURCE_PORT_KEY, ServerEventSourcePort())
        fetch_port = self._app._server_fetch_port or ServerFetchPort()
        self._di_scope.provide(FETCH_PORT_KEY, fetch_port)
        resource_port = getattr(self._app, "_server_resource_port", None)
        if resource_port is not None:
            self._di_scope.provide(RESOURCE_PORT_KEY, resource_port)
        self._di_scope.provide(FFI_PORT_KEY, ServerFFIPort())
        self._di_scope.provide(HISTORY_PORT_KEY, ServerHistoryPort(mode=router_mode))
        self._di_scope.provide(HOST_PORT_KEY, ServerHostPort())
        self._di_scope.provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        self._di_scope.provide(MEDIA_QUERY_PORT_KEY, ServerMediaQueryPort())
        self._di_scope.provide(TRANSITION_PORT_KEY, ServerTransitionPort())
        self._di_scope.provide(WEBSOCKET_PORT_KEY, ServerWebSocketPort())

    async def render_html(self, **kwargs: Any) -> str:
        return await generate_html(self, **kwargs)

    def get_pending_set_cookie_headers(self) -> list[str]:
        self._check_disposed()
        assert self._di_scope is not None
        port = self._di_scope.inject(COOKIE_PORT_KEY)
        if isinstance(port, ServerCookiePort):
            return port.get_pending_set_cookie_headers()
        return []
