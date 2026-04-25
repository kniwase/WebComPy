import asyncio
import mimetypes
import pathlib
from functools import partial
from operator import truth
from re import compile as re_compile
from re import escape as re_escape
from tempfile import TemporaryDirectory

import aiofiles
import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp

from webcompy.app._app import WebComPyApp
from webcompy.app._config import ServerConfig
from webcompy.cli._argparser import get_params
from webcompy.cli._html import PYSCRIPT_VERSION, generate_html
from webcompy.cli._lockfile import (
    LOCKFILE_NAME,
    get_bundled_deps,
    get_pyodide_package_names,
    resolve_lockfile,
    validate_local_environment,
)
from webcompy.cli._static_files import get_static_files
from webcompy.cli._utils import (
    discover_app,
    generate_app_version,
    get_server_config,
    get_webcompy_packge_dir,
)
from webcompy.cli._wheel_builder import get_stable_wheel_filename, make_webcompy_app_package


def create_asgi_app(
    app: WebComPyApp,
    server_config: ServerConfig | None = None,
) -> ASGIApp:
    if server_config is None:
        server_config = ServerConfig()

    lockfile, lockfile_errors, lockfile_warnings = resolve_lockfile(
        app.config.dependencies,
        PYSCRIPT_VERSION,
        app.config.app_package_path / LOCKFILE_NAME,
    )
    for warning in lockfile_warnings:
        print(f"Warning: {warning}", flush=True)
    for err in lockfile_errors:
        print(f"Error: {err}", flush=True)

    if lockfile is not None:
        env_errors, env_warnings = validate_local_environment(lockfile)
        for warning in env_warnings:
            print(f"Warning: {warning}", flush=True)
        for err in env_errors:
            print(f"Error: {err}", flush=True)
        lockfile_errors.extend(env_errors)

    if lockfile_errors:
        import sys

        print("Build failed due to lock file errors. Fix the above issues and try again.", file=sys.stderr)
        sys.exit(1)

    bundled_deps = get_bundled_deps(lockfile)
    pyodide_package_names = get_pyodide_package_names(lockfile)

    app_version = generate_app_version(app.config.version)

    with TemporaryDirectory() as temp:
        temp_path = pathlib.Path(temp)
        make_webcompy_app_package(
            temp_path,
            get_webcompy_packge_dir(),
            app.config.app_package_path,
            app_version,
            app.config.assets,
            bundled_deps=bundled_deps or None,
        )
        app_package_files: dict[str, tuple[bytes, str]] = {
            p.name: (
                p.open("rb").read(),
                t if (t := mimetypes.guess_type(str(p))[0]) else "application/octet-stream",
            )
            for p in temp_path.iterdir()
        }

    async def send_app_package_file(request: Request):
        filename: str = request.path_params.get("filename", "")  # type: ignore
        if filename in app_package_files:
            content, media_type = app_package_files[filename]
            headers: dict[str, str] = {}
            stable_wheel = get_stable_wheel_filename(app.config.app_package_path.name)
            if server_config.dev and filename == stable_wheel:
                headers["Cache-Control"] = "no-cache"
            return Response(content, media_type=media_type, headers=headers)
        else:
            raise HTTPException(404)

    app_package_files_route = Route(
        "/_webcompy-app-package/{filename:path}",
        send_app_package_file,
    )

    static_file_routes: list[Route] = []
    static_files_dir = server_config.static_files_dir_path.absolute()
    for relative_path in get_static_files(static_files_dir):
        static_file = static_files_dir / relative_path
        if (media_type := mimetypes.guess_type(str(static_file))[0]) is None:
            media_type = "application/octet-stream"

        async def send_file(request: Request, _static_file=static_file, _media_type=media_type):
            async with aiofiles.open(_static_file, "rb") as f:
                content = await f.read()
            return Response(content, media_type=_media_type)

        static_file_routes.append(Route("/" + relative_path, send_file))

    html_generator = partial(
        generate_html,
        app,
        server_config.dev,
        True,
        app_version,
        app.config.app_package_path.name,
        pyodide_package_names=pyodide_package_names or None,
    )
    base_url_stripper = partial(
        re_compile("^" + re_escape("/" + app.config.base_url.strip("/"))).sub,
        "",
    )

    if app.router_mode == "history" and app.routes:

        async def send_html(request: Request):  # type: ignore
            with app.di_scope:
                path: str = request.path_params.get("path", "")  # type: ignore
                requested_path = base_url_stripper(path).strip("/")
                accept_types: list[str] = request.headers.get("accept", "").split(",")
                routes = r if (r := app.routes) else []
                is_matched = truth(tuple(filter(lambda r: r[1](requested_path), routes)))
                if is_matched or "text/html" in accept_types:
                    app.set_path(requested_path)
                    return HTMLResponse(html_generator())
                else:
                    raise HTTPException(404)

        html_route = Route("/{path:path}", send_html)
    else:
        with app.di_scope:
            app.set_path("/")
            html = html_generator()

        async def send_html(_: Request):  # type: ignore
            return HTMLResponse(html)

        html_route = Route("/", send_html)

    if server_config.dev:

        async def loop():
            while True:
                await asyncio.sleep(60)
                yield None

        async def sse(_: Request):
            return EventSourceResponse(loop())

        dev_routes = [Route("/_webcompy_reload", endpoint=sse)]
    else:
        dev_routes: list[Route] = []

    return Starlette(
        routes=[
            *dev_routes,
            app_package_files_route,
            *static_file_routes,
            html_route,
        ]
    )


def run_server(app: WebComPyApp | None = None):
    _, args = get_params()
    if app is None:
        app_import_path = args.get("app")
        app, package = discover_app(app_import_path)
        server_config = get_server_config(package)
    else:
        server_config = ServerConfig()

    if args.get("dev"):
        server_config.dev = True
    port = args.get("port") or server_config.port
    asgi = create_asgi_app(app, server_config)
    uvicorn.run(asgi, host="0.0.0.0", port=port, reload=server_config.dev)
