import asyncio
from functools import partial
from operator import truth
from re import compile as re_compile, escape as re_escape
import mimetypes
import pathlib
from tempfile import TemporaryDirectory
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.routing import Route
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp
from sse_starlette.sse import EventSourceResponse
import uvicorn  # type: ignore
from webcompy.app._app import WebComPyApp
from webcompy.cli._argparser import get_params
from webcompy.cli._pyscript_wheel import make_webcompy_app_package_pyscript
from webcompy.cli._brython_cli import make_webcompy_app_package_brython
from webcompy.cli._config import WebComPyConfig
from webcompy.cli._html import generate_html
from webcompy.cli._utils import get_config, get_webcompy_packge_dir


def create_asgi_app(app: WebComPyApp, config: WebComPyConfig, dev_mode: bool = False) -> ASGIApp:
    with TemporaryDirectory() as temp:
        temp_path = pathlib.Path(temp)
        make_webcompy_app_package = (
            make_webcompy_app_package_pyscript
            if config.environment == "pyscript"
            else make_webcompy_app_package_brython
        )
        make_webcompy_app_package(
            temp_path,
            get_webcompy_packge_dir(),
            pathlib.Path(f"./{config.app_package}").absolute(),
        )
        app_package_files: dict[str, tuple[bytes, str]] = {
            p.name: (
                p.open("rb").read(),
                t if (t := mimetypes.guess_type(p)[0]) else "application/octet-stream",
            )
            for p in temp_path.iterdir()
        }

    async def send_app_package_file(request: Request):
        filename: str = request.path_params.get("filename", "")  # type: ignore
        if filename in app_package_files.keys():
            content, media_type = app_package_files[filename]
            return Response(content, media_type=media_type)
        else:
            raise HTTPException(404)

    html_generator = partial(generate_html, config, dev_mode, prerender=True)
    base_url_stripper = partial(
        re_compile("^" + re_escape("/" + config.base.strip("/"))).sub,
        "",
    )

    if app.__component__.router_mode == "history" and app.__component__.routes:
        html_route = config.base + "{path:path}"

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
                return HTMLResponse(html_generator(app))
            else:
                raise HTTPException(404)

    else:
        html_route = config.base
        app.__component__.set_path("/")
        html = html_generator(app)

        async def send_html(_: Request):  # type: ignore
            return HTMLResponse(html)

    routes = [
        Route(
            config.base + "webcompy-app-package/{filename:path}",
            send_app_package_file,
        ),
        Route(html_route, send_html),
    ]

    if dev_mode:

        async def loop():
            while True:
                await asyncio.sleep(60)
                yield None

        async def sse(_: Request):
            return EventSourceResponse(loop())

        routes.insert(0, Route(f"{config.base}_webcompy_reload", endpoint=sse))

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
