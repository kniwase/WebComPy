import asyncio
import mimetypes
import sys
from functools import partial
from operator import truth
from re import compile as re_compile
from re import escape as re_escape
from typing import Any, Literal

import aiofiles
import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp

from webcompy.app._app import WebComPyApp
from webcompy.di import inject
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy.ui.theme._server import read_theme_from_cookie
from webcompy_cli._argparser import get_params
from webcompy_cli._build import BuildArtifacts, resolve_build_artifacts
from webcompy_cli._static_files import get_static_files
from webcompy_cli._utils import discover_config
from webcompy_cli.config._build_config import WebComPyBuildConfig
from webcompy_server._html import generate_html


class _ServingApp:
    asgi: ASGIApp
    html_generator: partial[Any]
    hash_cache: list[str]
    artifacts: BuildArtifacts

    def __init__(
        self,
        asgi: ASGIApp,
        html_generator: partial[Any],
        hash_cache: list[str],
        artifacts: BuildArtifacts,
    ) -> None:
        self.asgi = asgi
        self.html_generator = html_generator
        self.hash_cache = hash_cache
        self.artifacts = artifacts


def create_asgi_app(
    app: WebComPyApp,
    build_config: WebComPyBuildConfig,
    *,
    mode: Literal["prod", "dev"] = "prod",
) -> _ServingApp:
    build_config.server.dev = mode == "dev"
    artifacts = resolve_build_artifacts(app, build_config, dev_mode=build_config.server.dev)

    base_url = app.config.base_url
    base_url_stripper = partial(
        re_compile("^" + re_escape("/" + base_url.strip("/"))).sub,
        "",
    )

    async def send_app_package_file(request: Request):
        filename: str = request.path_params.get("filename", "")  # type: ignore
        if artifacts.app_package_files and filename in artifacts.app_package_files:
            content, media_type = artifacts.app_package_files[filename]
            headers: dict[str, str] = {}
            if artifacts.dev_mode:
                if artifacts.fw_wheel_filename and filename == artifacts.fw_wheel_filename:
                    headers["Cache-Control"] = "max-age=86400, must-revalidate"
                else:
                    headers["Cache-Control"] = "no-cache"
            return Response(content, media_type=media_type, headers=headers)
        else:
            raise HTTPException(404)

    app_package_files_route = Route(
        "/_webcompy-app-package/{filename:path}",
        send_app_package_file,
    )

    wasm_asset_routes: list[Route] = []
    wasm_asset_files = artifacts.wasm_asset_files
    if wasm_asset_files is not None:  # wasm_asset_files is set only when wasm_serving == "local"

        async def send_wasm_asset(request: Request):
            filename: str = request.path_params.get("filename", "")  # type: ignore
            if filename in wasm_asset_files:
                asset_path = wasm_asset_files[filename]
                return FileResponse(asset_path, media_type="application/octet-stream")
            else:
                raise HTTPException(404)

        wasm_asset_routes.append(Route("/_webcompy-assets/packages/{filename:path}", send_wasm_asset))

    runtime_asset_routes: list[Route] = []
    runtime_asset_files = artifacts.runtime_asset_files
    if runtime_asset_files is not None:  # runtime_asset_files is set only when runtime_serving == "local"

        async def send_runtime_asset(request: Request):
            filename: str = request.path_params.get("filename", "")  # type: ignore
            if filename in runtime_asset_files:
                asset_path = runtime_asset_files[filename]
                media_type = mimetypes.guess_type(str(asset_path))[0] or "application/octet-stream"
                return FileResponse(asset_path, media_type=media_type)
            else:
                raise HTTPException(404)

        runtime_asset_routes.append(Route("/_webcompy-assets/{filename:path}", send_runtime_asset))

    static_file_routes: list[Route] = []
    static_files_dir = (build_config.app_package_path / build_config.static_files_dir).absolute()
    for relative_path in get_static_files(static_files_dir):
        static_file = static_files_dir / relative_path
        if (media_type := mimetypes.guess_type(str(static_file))[0]) is None:
            media_type = "application/octet-stream"

        async def send_file(request: Request, _static_file=static_file, _media_type=media_type):
            async with aiofiles.open(_static_file, "rb") as f:
                content = await f.read()
            return Response(content, media_type=_media_type)

        static_file_routes.append(Route("/" + relative_path, send_file))

    from webcompy.ui._styles import get_styles_file

    async def send_framework_ui_css(request: Request):
        filename: str = request.path_params.get("filename", "")  # type: ignore
        if "/" in filename or "\\" in filename or filename.startswith("."):
            raise HTTPException(404)
        content = get_styles_file(filename)
        if content is None:
            raise HTTPException(404)
        return Response(content, media_type="text/css")

    framework_ui_routes: list[Route] = [
        Route("/_webcompy-ui/{filename:path}", send_framework_ui_css),
    ]

    html_generator = partial(
        generate_html,
        app_package_name=build_config.app_package_path.name,
        dev_mode=artifacts.dev_mode,
        prerender=True,
        wheel_filename=artifacts.wheel_filename,
        pyodide_package_names=artifacts.pyodide_package_names,
        wasm_local_urls=artifacts.wasm_local_urls,
        lockfile_url=artifacts.lockfile_url,
        runtime_serving=artifacts.runtime_serving,
        extra_wheel_filenames=artifacts.extra_wheel_filenames,
    )

    # Mutable cache for hash-mode pre-rendered HTML
    _hash_cache: list[str] = []

    if app.router_mode == "history" and app.routes:

        async def send_html(request: Request):  # type: ignore
            path: str = request.path_params.get("path", "")  # type: ignore
            requested_path = base_url_stripper(path).strip("/")
            accept_types: list[str] = request.headers.get("accept", "").split(",")
            routes = r if (r := app.routes) else []
            is_matched = truth(tuple(filter(lambda r: r[1](requested_path), routes)))
            if is_matched or "text/html" in accept_types:
                cookie_header = request.headers.get("cookie", "")
                initial_theme = _read_initial_theme(cookie_header)
                ctx = app.create_render_context(
                    requested_path,
                    initial_theme=initial_theme,
                    cookie_header=cookie_header,
                )
                try:
                    return HTMLResponse(await html_generator(ctx))
                finally:
                    scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
                    await scheduler.await_pending()
                    ctx.dispose()
            else:
                raise HTTPException(404)

        html_route = Route("/{path:path}", send_html)
    else:

        async def send_html(request: Request):  # type: ignore
            if _hash_cache:
                return HTMLResponse(_hash_cache[0])
            cookie_header = request.headers.get("cookie", "")
            initial_theme = _read_initial_theme(cookie_header)
            ctx = app.create_render_context(
                "/",
                initial_theme=initial_theme,
                cookie_header=cookie_header,
            )
            try:
                return HTMLResponse(await html_generator(ctx))
            finally:
                scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
                await scheduler.await_pending()
                ctx.dispose()

        html_route = Route("/", send_html)

    if build_config.server.dev:

        async def loop():
            while True:
                await asyncio.sleep(60)
                yield None

        async def sse(_: Request):
            return EventSourceResponse(loop())

        dev_routes = [Route("/_webcompy_reload", endpoint=sse)]
    else:
        dev_routes: list[Route] = []

    routes: list[Route] = [
        *dev_routes,
        app_package_files_route,
        *wasm_asset_routes,
        *runtime_asset_routes,
        *framework_ui_routes,
        *static_file_routes,
        html_route,
    ]

    asgi = Starlette(routes=routes)

    fetch_port = app._server_fetch_port
    if fetch_port is not None:
        blocked_paths = [route[0] for route in (app.routes or []) if route[3] is not None]
        fetch_port.configure(asgi, blocked_paths, base_url=app.config.base_url)

    return _ServingApp(asgi=asgi, html_generator=html_generator, hash_cache=_hash_cache, artifacts=artifacts)


async def _pre_render_hash_mode_html(
    app: WebComPyApp,
    html_generator: partial,
    hash_cache: list[str],
) -> None:
    ctx = app.create_render_context("/")
    try:
        html = await html_generator(ctx)
        hash_cache.append(html)
    finally:
        ctx.dispose()


def _read_initial_theme(cookie_header: str) -> Any:
    if not cookie_header:
        return None
    return read_theme_from_cookie({"cookie": cookie_header})


def run_server(app: WebComPyApp | None = None):
    _, args = get_params()
    if app is None:
        build_config = discover_config(args.get("config"))
        app = build_config.app
    else:
        import types as _types

        app_module = None
        for mod in sys.modules.values():
            if isinstance(mod, _types.ModuleType) and mod.__name__ == app.__class__.__module__:
                continue
            if isinstance(mod, _types.ModuleType) and hasattr(mod, "app") and mod.app is app:
                app_module = mod
                break
        if app_module is None:
            from pathlib import Path as _Path

            app_module = _types.ModuleType("_webcompy_app")
            app_module.__file__ = str(_Path.cwd())
            app_module.app = app
        build_config = WebComPyBuildConfig(app_module)

    serve_all_deps = args.get("serve_all_deps")
    if serve_all_deps is not None:
        build_config.serve_all_deps = serve_all_deps
    wasm_serving = args.get("wasm_serving")
    if wasm_serving is not None:
        build_config.wasm_serving = wasm_serving
        build_config._explicit_wasm_serving = wasm_serving
    runtime_serving = args.get("runtime_serving")
    if runtime_serving is not None:
        build_config.runtime_serving = runtime_serving
        build_config._explicit_runtime_serving = runtime_serving
    standalone = args.get("standalone")
    if standalone is not None:
        build_config.standalone = standalone
    wheel_mode = args.get("wheel_mode")
    if wheel_mode is not None:
        build_config.wheel_mode = wheel_mode
    build_config.resolve_standalone()

    port = args.get("port") or build_config.server.port
    assert app is not None
    mode = "dev" if args.get("dev") else "prod"
    serving = create_asgi_app(app, build_config, mode=mode)

    if app.router_mode != "history":
        asyncio.run(_pre_render_hash_mode_html(app, serving.html_generator, serving.hash_cache))

    uvicorn.run(serving.asgi, host="0.0.0.0", port=port, reload=build_config.server.dev)
