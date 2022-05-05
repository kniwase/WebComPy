from functools import partial
from re import compile as re_compile, escape as re_escape
import mimetypes
import pathlib
from tempfile import TemporaryDirectory
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse
from starlette.routing import Route
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp
import uvicorn  # type: ignore
from webcompy.cli._argparser import get_params
from webcompy.cli._brython_cli import (
    install_brython_scripts,
    make_brython_package,
)
from webcompy.cli._config import WebComPyConfig
from webcompy.cli._html import generate_html
from webcompy.cli._utils import get_app, get_config


def create_asgi_app(config: WebComPyConfig, dev_mode: bool = False) -> ASGIApp:
    with TemporaryDirectory() as temp:
        install_brython_scripts(temp)
        make_brython_package("webcompy", temp)
        make_brython_package("dev", temp)
        script_files: dict[str, tuple[bytes, str]] = {
            p.name: (
                p.open("rb").read(),
                t if (t := mimetypes.guess_type(p)[0]) else "application/octet-stream",
            )
            for p in pathlib.Path(temp).iterdir()
        }

    async def send_script_file(request: Request):
        filename: str = request.path_params.get("filename", "")  # type: ignore
        if filename in script_files.keys():
            content, media_type = script_files[filename]
            return PlainTextResponse(content, media_type=media_type)
        else:
            raise HTTPException(404)

    app = get_app(config)
    html_generator = partial(generate_html, config, dev_mode)
    base_url_stripper = partial(re_compile("^" + re_escape(config.base)).sub, "")

    if app.__component__.router_mode == "history" and app.__component__.routes:

        async def send_html(request: Request):  # type: ignore
            # get requested path
            path: str = request.path_params.get("path", "")  # type: ignore
            requested_path = base_url_stripper(path).strip("/")
            # get accept types
            accept_types: list[str] = request.headers.get("accept", "").split(",")
            # search requested page
            routes = r if (r := app.__component__.routes) else []
            matched = [
                route
                for route, match_targeted_routes, _, _ in routes
                if match_targeted_routes(requested_path)
            ]
            # response html
            if matched:
                app.__component__.set_path(matched[0])
                return HTMLResponse(html_generator(app, True))
            elif "text/html" in accept_types:
                app.__component__.set_path(requested_path)
                return HTMLResponse(html_generator(app, True))
            else:
                raise HTTPException(404)

        html_route = (
            config.base + "/{path:path}" if config.base != "/" else "/{path:path}"
        )

    else:

        async def send_html(_: Request):  # type: ignore
            return HTMLResponse(html)

        html_route = config.base + "/" if config.base != "/" else "/"
        html = html_generator(app, False)

    routes = [
        Route("/_scripts/{filename:path}", send_script_file),
        Route(html_route, send_html),
    ]
    return Starlette(routes=routes)


def run_server():
    _, args = get_params()
    config = get_config()
    port = config.server_port if args["port"] is None else args["port"]
    uvicorn.run("webcompy.cli._asgi_app:app", port=port, reload=args["dev"])
