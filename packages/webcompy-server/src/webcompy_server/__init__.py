from webcompy_server._context import ServerRenderContext
from webcompy_server._html import generate_html


def configure_server_context(app):
    app._render_context_class = ServerRenderContext


__all__ = [
    "ServerRenderContext",
    "configure_server_context",
    "generate_html",
]
