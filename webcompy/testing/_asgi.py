from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route

from webcompy.cli._html import _HtmlElement

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.types import ASGIApp

    from webcompy.app._app import WebComPyApp


def format_html(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    return str(soup)


def render_app_html(app: WebComPyApp, path: str = "/", **kwargs: Any) -> str:
    from webcompy.cli._html import generate_html

    ctx = app.create_render_context(path)
    try:
        return generate_html(ctx, **kwargs)
    finally:
        ctx.dispose()


def create_test_asgi_app(app: WebComPyApp) -> ASGIApp:

    if app.router_mode == "history" and app.routes:

        async def _send_html(request: Request) -> HTMLResponse:
            path: str = request.path_params.get("path", "")
            ctx = app.create_render_context(path.strip("/"))
            try:
                html = _HtmlElement("div", {}, ctx._root).render_html()
                return HTMLResponse(html)
            finally:
                ctx.dispose()

        html_route = Route("/{path:path}", _send_html)
    else:

        async def _send_html_static(_: Request) -> HTMLResponse:
            ctx = app.create_render_context("/")
            try:
                html = _HtmlElement("div", {}, ctx._root).render_html()
                return HTMLResponse(html)
            finally:
                ctx.dispose()

        html_route = Route("/", _send_html_static)

    return Starlette(routes=[html_route])
