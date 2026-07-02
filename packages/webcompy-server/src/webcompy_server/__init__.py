from webcompy_server._context import ServerRenderContext
from webcompy_server._html import generate_html
from webcompy_server.ports._fetch import ServerFetchPort


def configure_server_context(app):
    app._render_context_class = ServerRenderContext
    app._server_fetch_port = ServerFetchPort()


__all__ = [
    "ServerRenderContext",
    "configure_server_context",
    "generate_html",
]
