"""ASGI test helpers for rendering WebComPy apps to HTML."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route

from webcompy.di import inject
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy_server import configure_server_context
from webcompy_server._html import _HtmlElement
from webcompy_testing._utils import run_sync

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.types import ASGIApp

    from webcompy.app._app import WebComPyApp


def format_html(html: str) -> str:
    """Format raw HTML for readable output.

    Args:
        html: Raw HTML string to format.

    Returns:
        Pretty-printed HTML string produced by BeautifulSoup.

    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    return str(soup)


async def render_app_html(app: WebComPyApp, path: str = "/", **kwargs: Any) -> str:
    from webcompy_server._html import generate_html

    configure_server_context(app)
    ctx = app.create_render_context(path)
    try:
        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
        await scheduler.await_pending()
        return await generate_html(ctx, **kwargs)
    finally:
        ctx.dispose()


def render_app_html_sync(app: WebComPyApp, path: str = "/", **kwargs: Any) -> str:
    """Render an app to an HTML string synchronously.

    Args:
        app: Application to render.
        path: Route path to render.
        **kwargs: Additional options forwarded to ``generate_html``.

    Returns:
        Rendered HTML string for the requested path.

    """
    return run_sync(render_app_html(app, path, **kwargs))


def create_test_asgi_app(app: WebComPyApp) -> ASGIApp:
    """Create a Starlette ASGI app that renders the WebComPy app.

    Args:
        app: Application to serve via the test ASGI app.

    Returns:
        An ``ASGIApp`` that renders the WebComPy app for incoming requests.

    """

    configure_server_context(app)

    if app.router_mode == "history" and app.routes:

        async def _send_html(request: Request) -> HTMLResponse:
            path: str = request.path_params.get("path", "")
            ctx = app.create_render_context(path.strip("/"))
            try:
                scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
                await scheduler.await_pending()
                html = await _HtmlElement("div", {}, ctx._root).render_html()
                return HTMLResponse(html)
            finally:
                ctx.dispose()

        html_route = Route("/{path:path}", _send_html)
    else:

        async def _send_html_static(_: Request) -> HTMLResponse:
            ctx = app.create_render_context("/")
            try:
                scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
                await scheduler.await_pending()
                html = await _HtmlElement("div", {}, ctx._root).render_html()
                return HTMLResponse(html)
            finally:
                ctx.dispose()

        html_route = Route("/", _send_html_static)

    return Starlette(routes=[html_route])
