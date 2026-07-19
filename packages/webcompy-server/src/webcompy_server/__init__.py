from webcompy_server._context import ServerRenderContext
from webcompy_server._html import generate_html
from webcompy_server.ports._fetch import ServerFetchPort
from webcompy_server.ports._resource import ServerResourcePort


def configure_server_context(
    app,
    *,
    resource_port: ServerResourcePort | None = None,
) -> None:
    app._render_context_class = ServerRenderContext
    app._server_fetch_port = ServerFetchPort()
    if resource_port is not None:
        app._server_resource_port = resource_port


__all__ = [
    "ServerRenderContext",
    "configure_server_context",
    "generate_html",
]
