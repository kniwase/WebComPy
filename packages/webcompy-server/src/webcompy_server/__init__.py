from __future__ import annotations

from typing import TYPE_CHECKING

from webcompy_server._context import ServerRenderContext
from webcompy_server._html import generate_html
from webcompy_server.ports._fetch import ServerFetchPort
from webcompy_server.ports._resource import ServerResourcePort

if TYPE_CHECKING:
    from starlette.types import ASGIApp


def configure_server_context(
    app,
    *,
    resource_port: ServerResourcePort | None = None,
    root_app: ASGIApp | None = None,
) -> None:
    app._render_context_class = ServerRenderContext
    fetch_port = ServerFetchPort()
    app._server_fetch_port = fetch_port
    if resource_port is not None:
        app._server_resource_port = resource_port
    if root_app is not None:
        prefix = app.config.base_url.strip("/")
        blocked_paths = [
            f"{prefix}/{route[0]}" if route[0] else prefix for route in (app.routes or []) if route[3] is not None
        ]
        fetch_port.configure(
            root_app,
            blocked_paths,
            base_url=app.config.base_url,
            embedded=True,
        )


__all__ = [
    "ServerRenderContext",
    "configure_server_context",
    "generate_html",
]
