import asyncio
from functools import partial
from operator import truth
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
from sse_starlette.sse import EventSourceResponse
import uvicorn  # type: ignore
from webcompy.cli._argparser import get_params
from webcompy.cli._brython_cli import (
    install_brython_scripts,
    make_brython_package,
)
from webcompy.cli._config import WebComPyConfig
from webcompy.cli._html import generate_html
from webcompy.cli._utils import (
    get_app,
    get_config,
    get_webcompy_packge_dir,
)


def create_asgi_app(config: WebComPyConfig, dev_mode: bool = False) -> ASGIApp:
    app = get_app(config)
    
    with TemporaryDirectory() as temp:
        install_brython_scripts(temp)
        make_brython_package(get_webcompy_packge_dir(), temp)
        make_brython_package(
            str(pathlib.Path(f"./{config.app_package}").absolute()), temp
        )
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

    html_generator = partial(generate_html, config, dev_mode)
    base_url_stripper = partial(re_compile("^" + re_escape(config.base)).sub, "")

    if app.__component__.router_mode == "history" and app.__component__.routes:
        html_route = (
            config.base + "/{path:path}" if config.base != "/" else "/{path:path}"
        )

        async def send_html(request: Request):  # type: ignore
            # get requested path
            path: str = request.path_params.get("path", "")  # type: ignore
            requested_path = base_url_stripper(path).strip("/")
            # get accept types
            accept_types: list[str] = request.headers.get("accept", "").split(",")
            # search requested page
            routes = r if (r := app.__component__.routes) else []
            is_matched = truth(tuple(filter(lambda r: r[1](requested_path), routes)))
            # response html
            if is_matched or "text/html" in accept_types:
                app.__component__.set_path(requested_path)
                return HTMLResponse(html_generator(app, True))
            else:
                raise HTTPException(404)

    else:
        html_route = config.base
        html = html_generator(app, False)

        async def send_html(_: Request):  # type: ignore
            return HTMLResponse(html)

    if (base := config.base) != "/":
        base = f"{base}/"
    routes = [
        Route(base + "scripts/{filename:path}", send_script_file),
        Route(html_route, send_html),
    ]

    if dev_mode:

        async def loop():
            while True:
                await asyncio.sleep(60)
                yield None

        async def sse(_: Request):
            return EventSourceResponse(loop())

        if config.base == "/":
            reload_route = "/_webcompy_reload"
        else:
            reload_route = f"{config.base}/_webcompy_reload"
        routes.insert(0, Route(reload_route, endpoint=sse))

    return Starlette(routes=routes)


def run_server():
    _, args = get_params()
    config = get_config()
    uvicorn.run(
        "webcompy.cli._asgi_app:app",
        host="0.0.0.0",
        port=port if (port := args["port"]) else config.server_port,
        reload=args["dev"],
    )
