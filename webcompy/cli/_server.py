import mimetypes
import pathlib
from tempfile import TemporaryDirectory
from fastapi import FastAPI, HTTPException
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
    index_html = generate_html(
        app_package_name=config.app_package,
        component_styles=app.__component_styles__,
        base=config.base,
        dev_mode=dev_mode,
    ).render_html()

    if app.__router_mode__ == "history" and app.__routes__:
        for route in app.__routes__:

            @fastapi_app.get(f"/{route}")
            async def _():
                return HTMLResponse(index_html)

    else:

        @fastapi_app.get("/")
        async def _():
            return HTMLResponse(index_html)

    return fastapi_app


def run_server():
    _, args = get_params()
    config = get_config()
    port = config.server_port if args["port"] is None else args["port"]
    uvicorn.run("webcompy.cli._asgi_app:app", port=port, reload=args["dev"])
