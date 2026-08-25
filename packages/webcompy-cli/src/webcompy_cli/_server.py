"""ASGI application factory and development server runner."""

import asyncio
import mimetypes
import sys
from functools import partial
from operator import truth
from re import compile as re_compile
from re import escape as re_escape
from typing import Any, Literal, cast

import aiofiles
import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, Response
from starlette.routing import BaseRoute, Mount, Route, WebSocketRoute
from starlette.types import ASGIApp

from webcompy.app._app import WebComPyApp
from webcompy.di import inject
from webcompy.exception import WebComPyException
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy.rpc._registry import ProcedureRegistry
from webcompy.ui.theme._server import read_theme_from_cookie
from webcompy_cli._argparser import get_params
from webcompy_cli._build import BuildArtifacts, resolve_build_artifacts
from webcompy_cli._static_files import get_static_files
from webcompy_cli._utils import discover_config
from webcompy_cli.config._build_config import WebComPyBuildConfig
from webcompy_server._context import ServerRenderContext
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


def _normalize_mount_prefix(prefix: str) -> str:
    return "/" + prefix.strip("/") if prefix.strip("/") else "/"


def _page_static_prefix(path: str) -> list[str]:
    segments: list[str] = []
    for seg in path.strip("/").split("/"):
        if not seg or "{" in seg:
            break
        segments.append(seg)
    return segments


def _resolve_mounts(app: WebComPyApp, build_config: WebComPyBuildConfig) -> list[tuple[str, ASGIApp]]:
    mounts_factory = build_config.server.mounts
    if mounts_factory is None:
        return []

    mount_map = mounts_factory()
    if not isinstance(mount_map, dict):
        raise WebComPyException(
            f"WebComPyServerConfig.mounts callable must return a dict[str, ASGIApp], got {type(mount_map).__name__}"
        )
    conflicts: list[str] = []
    resolved: list[tuple[str, ASGIApp]] = []
    for prefix, asgi_app in mount_map.items():
        normalized = _normalize_mount_prefix(prefix)
        if normalized == "/":
            conflicts.append(f"  '{prefix}': mounting at '/' would shadow all page routes")
            continue
        if normalized.startswith("/_webcompy"):
            conflicts.append(f"  '{prefix}': prefixes starting with '/_webcompy' are reserved by the framework")
            continue
        mount_segments = normalized.strip("/").split("/")
        for route in app.routes or []:
            static = _page_static_prefix(route[0])
            if len(static) >= len(mount_segments) and static[: len(mount_segments)] == mount_segments:
                conflicts.append(f"  '{prefix}': collides with page route '/{route[0]}'")
        resolved.append((normalized, asgi_app))

    if conflicts:
        raise WebComPyException("ASGI mount path collisions detected:\n" + "\n".join(dict.fromkeys(conflicts)))
    return resolved


def _make_rpc_route(registry: ProcedureRegistry, path: str) -> Route:
    from webcompy_server.rpc import create_dispatcher_app

    return Route(path, create_dispatcher_app(registry), methods=["POST"])


def _make_rpc_ws_route(registry: ProcedureRegistry, path: str) -> WebSocketRoute:
    from webcompy_server.rpc import create_rpc_ws_endpoint

    return WebSocketRoute(path, create_rpc_ws_endpoint(registry))


def create_asgi_app(
    app: WebComPyApp,
    build_config: WebComPyBuildConfig,
    *,
    mode: Literal["prod", "dev"] = "prod",
) -> _ServingApp:
    """Create the ASGI application for serving the WebComPy app.

    Resolves build artifacts, wires static, asset, and resource routes,
    and mounts the HTML and optional RPC and dev-reload routes.

    Args:
        app: Application instance to serve.
        build_config: Build configuration controlling artifact resolution.
        mode: Serving mode, ``"prod"`` or ``"dev"``.

    Returns:
        A ``_ServingApp`` wrapping the ASGI app and its artifacts.

    """
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

    resource_routes: list[Route] = []
    resource_allow_list = artifacts.resource_allow_list
    if resource_allow_list is not None:
        base_url_stripped = "/" + app.config.base_url.strip("/") if app.config.base_url.strip("/") else ""

        async def send_resource(request: Request):
            path: str = request.path_params.get("path", "")  # type: ignore
            if path not in resource_allow_list:  # type: ignore[operator]
                raise HTTPException(404)
            try:
                resolved = (build_config.app_package_path / path).resolve()
                resolved.relative_to(build_config.app_package_path.resolve())
            except (ValueError, OSError):
                raise HTTPException(403) from None
            media_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            headers: dict[str, str] = {}
            if artifacts.dev_mode:
                headers["Cache-Control"] = "no-cache, must-revalidate"
            else:
                headers["Cache-Control"] = "public, max-age=3600"
            return FileResponse(resolved, media_type=media_type, headers=headers)

        resource_routes.append(Route(base_url_stripped + "/_webcompy-resource/{path:path}", send_resource))
        if base_url_stripped:
            resource_routes.append(Route("/_webcompy-resource/{path:path}", send_resource))

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
        app_package_path=build_config.app_package_path,
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
                assert isinstance(ctx, ServerRenderContext)
                try:
                    scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
                    await scheduler.await_pending()
                    response = HTMLResponse(await html_generator(ctx))
                    for header in ctx.get_pending_set_cookie_headers():
                        response.headers.append("set-cookie", header)
                    return response
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

    mount_entries = _resolve_mounts(app, build_config)
    mount_routes: list[BaseRoute] = [Mount(path=prefix, app=mounted) for prefix, mounted in mount_entries]

    rpc_routes: list[BaseRoute] = []
    rpc_mount_prefixes: list[str] = []
    rpc_registry = app.rpc
    if rpc_registry.has_procedures:
        rpc_routes.append(_make_rpc_route(rpc_registry, rpc_registry.path))
        rpc_routes.append(_make_rpc_ws_route(rpc_registry, rpc_registry.path))
        prefixed_rpc_path = app.config.base_url.rstrip("/") + rpc_registry.path
        if prefixed_rpc_path != rpc_registry.path:
            rpc_routes.append(_make_rpc_route(rpc_registry, prefixed_rpc_path))
            rpc_routes.append(_make_rpc_ws_route(rpc_registry, prefixed_rpc_path))
            rpc_mount_prefixes.append(prefixed_rpc_path)

    routes: list[BaseRoute] = [
        *dev_routes,
        app_package_files_route,
        *wasm_asset_routes,
        *runtime_asset_routes,
        *framework_ui_routes,
        *resource_routes,
        *static_file_routes,
        *mount_routes,
        *rpc_routes,
        html_route,
    ]

    asgi = Starlette(routes=routes)

    fetch_port = app._server_fetch_port
    if fetch_port is not None:
        blocked_paths = [route[0] for route in (app.routes or []) if route[3] is not None]
        fetch_port.configure(
            asgi,
            blocked_paths,
            base_url=app.config.base_url,
            mount_prefixes=[prefix for prefix, _ in mount_entries] + rpc_mount_prefixes,
        )

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
    """Run the development or production ASGI server.

    Args:
        app: Application instance to serve. When ``None``, the
            configuration is discovered via ``discover_config`` and CLI
            flags override the build and server options.

    """
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
            cast("Any", app_module).app = app
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
