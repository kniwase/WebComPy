from __future__ import annotations

from typing import TYPE_CHECKING

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


def create_test_asgi_app(app: WebComPyApp) -> ASGIApp:

    if app.router_mode == "history" and app.routes:

        async def _send_html(request: Request) -> HTMLResponse:
            with app.di_scope:
                path: str = request.path_params.get("path", "")
                app.set_path(path.strip("/"))
                html = _HtmlElement("div", {}, app._root).render_html()
                return HTMLResponse(html)

        html_route = Route("/{path:path}", _send_html)
    else:
        with app.di_scope:
            app.set_path("/")
            prerendered_html = _HtmlElement("div", {}, app._root).render_html()

        async def _send_html_static(_: Request) -> HTMLResponse:
            return HTMLResponse(prerendered_html)

        html_route = Route("/", _send_html_static)

    return Starlette(routes=[html_route])
