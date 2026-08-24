"""Server-side rendering entry points for WebComPy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from webcompy_server._context import ServerRenderContext
from webcompy_server._html import generate_html
from webcompy_server.ports._fetch import ServerFetchPort
from webcompy_server.ports._resource import ServerResourcePort

if TYPE_CHECKING:
    from starlette.types import ASGIApp

    from webcompy.app import WebComPyApp


def configure_server_context(
    app: WebComPyApp,
    *,
    resource_port: ServerResourcePort | None = None,
    root_app: ASGIApp | None = None,
) -> None:
    """Switch a ``WebComPyApp`` to server-side rendering.

    Sets ``ServerRenderContext`` as the application's render context
    class and installs a fresh ``ServerFetchPort``, preserving any
    external HTTP client configured on a previously installed server
    fetch port.

    Args:
        app: Application to switch to server-side rendering.
        resource_port: Optional ``ServerResourcePort`` serving
            app-package resources; when ``None``, any existing resource
            port is left unchanged.
        root_app: Optional host ASGI application used for self-site
            fetches. When given, page routes under the configured base
            URL are blocked during SSR to prevent recursive self-fetches,
            and the fetch port is marked as embedded.

    """
    app._render_context_class = ServerRenderContext
    old_port = app._server_fetch_port
    fetch_port = ServerFetchPort(external_client=old_port._external_client if old_port is not None else None)
    app._server_fetch_port = fetch_port
    if resource_port is not None:
        app._server_resource_port = resource_port
    if root_app is not None:
        prefix = app.config.base_url.strip("/")
        blocked_paths = [
            f"{prefix}/{route[0].lstrip('/')}" if route[0] else prefix
            for route in (app.routes or [])
            if route[3] is not None
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
