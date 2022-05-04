from functools import partial
from re import compile as re_compile, escape as re_escape
import mimetypes
import pathlib
from tempfile import TemporaryDirectory
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse, PlainTextResponse
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

    fastapi_app = FastAPI()

    @fastapi_app.get("/_scripts/{filename}")
    async def _(filename: str):
        if filename in script_files.keys():
            content, media_type = script_files[filename]
            return PlainTextResponse(content, media_type=media_type)
        else:
            raise HTTPException(404)

    app = get_app(config)
    html_generator = partial(
        generate_html,
        config.app_package,
        app.__component__.style,
        config.base,
        dev_mode,
    )
    base_url_stripper = partial(re_compile("^" + re_escape(config.base)).sub, "")

    if app.__component__.router_mode == "history" and app.__component__.routes:
        routes = r if (r := app.__component__.routes) else []
        if config.base != "/":
            endpoint = config.base + "/{path:path}"
        else:
            endpoint = "/{path:path}"

        @fastapi_app.get(endpoint)
        async def _(path: str, accept: str | None = Header(None)):
            requested_path = base_url_stripper(path).strip("/")
            accept_types = (accept if accept else "").split(",")
            matched = [
                route
                for route, match_targeted_routes, _, _ in routes
                if match_targeted_routes(requested_path)
            ]
            if matched:
                app.__component__.set_path(matched[0])
                return HTMLResponse(html_generator(app.__component__))
            elif "text/html" in accept_types:
                app.__component__.set_path(requested_path)
                return HTMLResponse(html_generator(app.__component__))
            else:
                raise HTTPException(404)

    else:
        if config.base != "/":
            endpoint = config.base + "/"
        else:
            endpoint = "/"
        html = html_generator(None)

        @fastapi_app.get(endpoint)
        async def _():
            return HTMLResponse(html)

    return fastapi_app


def run_server():
    _, args = get_params()
    config = get_config()
    port = config.server_port if args["port"] is None else args["port"]
    uvicorn.run("webcompy.cli._asgi_app:app", port=port, reload=args["dev"])
