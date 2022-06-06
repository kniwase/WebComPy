import asyncio
from functools import partial
from operator import truth
from re import compile as re_compile, escape as re_escape
import mimetypes
import pathlib
from tempfile import TemporaryDirectory
import aiofiles
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
from webcompy.cli._pyscript_wheel import make_webcompy_app_package
from webcompy.cli._config import WebComPyConfig
from webcompy.cli._html import generate_html
from webcompy.cli._utils import (
    get_config,
    get_webcompy_packge_dir,
    generate_app_version,
)
from webcompy.cli._static_files import get_static_files


def create_asgi_app(
    app: WebComPyApp, config: WebComPyConfig, dev_mode: bool = False
) -> ASGIApp:
    app_version = generate_app_version()

    # App Packages
    with TemporaryDirectory() as temp:
        temp_path = pathlib.Path(temp)
        make_webcompy_app_package(
            temp_path,
            get_webcompy_packge_dir(),
            config.app_package_path,
            app_version,
        )
        app_package_files: dict[str, tuple[bytes, str]] = {
            p.name: (
                p.open("rb").read(),
                t
                if (t := mimetypes.guess_type(str(p))[0])
                else "application/octet-stream",
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

    app_package_files_route = Route(
        "/_webcompy-app-package/{filename:path}",
        send_app_package_file,
    )

    # Static Files
    static_file_routes: list[Route] = []
    static_files_dir = pathlib.Path(f"./{config.static_files_dir}").absolute()
    for relative_path in get_static_files(static_files_dir):
        static_file = static_files_dir / relative_path
        if (media_type := mimetypes.guess_type(str(static_file))[0]) is None:
            media_type = "application/octet-stream"

        async def send_file(request: Request):
            async with aiofiles.open(static_file, "rb") as f:
                content = await f.read()
            return Response(content, media_type=media_type)

        static_file_routes.append(Route("/" + relative_path, send_file))

    # HTMLs
    html_generator = partial(generate_html, config, dev_mode, True, app_version)
    base_url_stripper = partial(
        re_compile("^" + re_escape("/" + config.base.strip("/"))).sub,
        "",
    )

    if app.__component__.router_mode == "history" and app.__component__.routes:

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

        html_route = Route("/{path:path}", send_html)
    else:
        app.__component__.set_path("/")
        html = html_generator(app)

        async def send_html(_: Request):  # type: ignore
            return HTMLResponse(html)

        html_route = Route("/", send_html)

    # Hot Reloader
    if dev_mode:

        async def loop():
            while True:
                await asyncio.sleep(60)
                yield None

        async def sse(_: Request):
            return EventSourceResponse(loop())

        dev_routes = [Route("/_webcompy_reload", endpoint=sse)]
    else:
        dev_routes: list[Route] = []

    # Declare ASGI App
    return Starlette(
        routes=[
            *dev_routes,
            app_package_files_route,
            *static_file_routes,
            html_route,
        ]
    )


def run_server():
    _, args = get_params()
    config = get_config()
    uvicorn.run(
        "webcompy.cli._asgi_app:app",
        host="0.0.0.0",
        port=port if (port := args["port"]) else config.server_port,
        reload=args["dev"],
    )
