import asyncio
import mimetypes
import pathlib
import sys
from functools import partial
from operator import truth
from re import compile as re_compile
from re import escape as re_escape
from tempfile import TemporaryDirectory
from typing import Any

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
from webcompy.cli._argparser import get_params
from webcompy.cli._html import PYSCRIPT_VERSION, generate_html
from webcompy.cli._lockfile import (
    LOCKFILE_NAME,
    get_bundled_deps,
    get_cdn_pure_python_package_names,
    get_wasm_package_names,
    resolve_lockfile,
    validate_local_environment,
    verify_and_update_runtime_assets,
)
from webcompy.cli._lockfile_sync import resolve_dependencies
from webcompy.cli._pyodide_downloader import (
    PyodideDownloadError,
    download_pyodide_wheel,
    download_wasm_wheels,
    extract_wheel,
)
from webcompy.cli._pyodide_lock import PYODIDE_LOCK_URL_TEMPLATE
from webcompy.cli._runtime_downloader import RuntimeDownloadError, download_runtime_assets
from webcompy.cli._static_files import get_static_files
from webcompy.cli._utils import (
    discover_config,
    ensure_webcompy_modules_dir,
    generate_app_version,
    get_webcompy_packge_dir,
)
from webcompy.cli._wheel_builder import (
    make_browser_webcompy_wheel,
    make_webcompy_app_package,
)
from webcompy.cli.config._build_config import WebComPyBuildConfig
from webcompy.ui.theme._server import read_theme_from_cookie


def create_asgi_app(
    app: WebComPyApp,
    build_config: WebComPyBuildConfig,
) -> ASGIApp:
    build_config.server = build_config.server

    modules_dir = build_config.app_package_path / ".webcompy_modules"
    ensure_webcompy_modules_dir(modules_dir)
    resolve_dependencies(build_config)
    assert build_config.dependencies is not None

    lockfile, lockfile_errors, lockfile_warnings = resolve_lockfile(
        build_config.dependencies,
        PYSCRIPT_VERSION,
        build_config.app_package_path / LOCKFILE_NAME,
        modules_dir,
        wasm_serving=build_config.wasm_serving or "cdn",
        runtime_serving=build_config.runtime_serving or "cdn",
        standalone=build_config.standalone,
    )
    for warning in lockfile_warnings:
        print(f"Warning: {warning}", file=sys.stderr, flush=True)
    for err in lockfile_errors:
        print(f"Error: {err}", file=sys.stderr, flush=True)

    if lockfile is not None:
        env_errors, env_warnings = validate_local_environment(lockfile, serve_all_deps=build_config.serve_all_deps)
        for warning in env_warnings:
            print(f"Warning: {warning}", file=sys.stderr, flush=True)
        for err in env_errors:
            print(f"Error: {err}", file=sys.stderr, flush=True)
        lockfile_errors.extend(env_errors)

    if lockfile_errors:
        print("Build failed due to lock file errors. Fix the above issues and try again.", file=sys.stderr)
        sys.exit(1)

    resolved_wasm_serving = build_config.wasm_serving or "cdn"

    bundled_deps = get_bundled_deps(lockfile, serve_all_deps=build_config.serve_all_deps)
    wasm_package_names = get_wasm_package_names(lockfile)

    wasm_local_urls: dict[str, str] | None = None
    lockfile_url: str | None = None
    wasm_asset_files: dict[str, pathlib.Path] = {}
    if resolved_wasm_serving == "local" and lockfile is not None:
        pyodide_version = lockfile.pyodide_version
        lockfile_url = PYODIDE_LOCK_URL_TEMPLATE.format(version=pyodide_version)

        downloaded_paths = download_wasm_wheels(lockfile, modules_dir)
        base_url = app.config.base_url
        wasm_local_urls = {}
        for name, entry in lockfile.wasm_packages.items():
            if entry.file_name and entry.sha256:
                wasm_local_urls[name] = f"{base_url}_webcompy-assets/packages/{entry.file_name}"
                if name in downloaded_paths:
                    wasm_asset_files[entry.file_name] = downloaded_paths[name]

    resolved_runtime_serving = build_config.runtime_serving or "cdn"

    runtime_asset_files: dict[str, pathlib.Path] = {}
    if resolved_runtime_serving == "local":
        try:
            runtime_results = download_runtime_assets(
                lockfile.pyodide_version if lockfile else "0.29.3",
                PYSCRIPT_VERSION,
                modules_dir,
                lock_file=lockfile,
            )
            if lockfile is not None:
                verify_and_update_runtime_assets(
                    runtime_results,
                    lockfile,
                    PYSCRIPT_VERSION,
                    build_config.app_package_path / LOCKFILE_NAME,
                )
            for rel_path, (asset_path, _sha256) in runtime_results.items():
                runtime_asset_files[rel_path] = asset_path
        except RuntimeDownloadError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        lockfile_url = None

    cdn_pure_python_names: list[str] = []
    cdn_extracted_deps: list[tuple[str, pathlib.Path]] = []
    cdn_temp_dir_obj = None
    if not build_config.serve_all_deps:
        cdn_pure_python_names = get_cdn_pure_python_package_names(lockfile)
    elif lockfile is not None:
        for name, entry in lockfile.pure_python_packages.items():
            if entry.in_pyodide_cdn and entry.pyodide_file_name and entry.pyodide_sha256:
                try:
                    wheel_path = download_pyodide_wheel(
                        entry.pyodide_file_name,
                        lockfile.pyodide_version,
                        entry.pyodide_sha256,
                        modules_dir,
                    )
                except PyodideDownloadError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    sys.exit(1)
                if cdn_temp_dir_obj is None:
                    cdn_temp_dir_obj = TemporaryDirectory()
                    cdn_temp_dir_obj.__enter__()
                extract_dest = pathlib.Path(cdn_temp_dir_obj.name) / name
                extract_dest.mkdir(parents=True, exist_ok=True)
                extracted = extract_wheel(wheel_path, extract_dest)
                cdn_extracted_deps.extend(extracted)

    if cdn_temp_dir_obj is not None:
        cdn_temp_dir_obj.__exit__(None, None, None)

    all_bundled_deps = bundled_deps + cdn_extracted_deps

    app_version = generate_app_version(build_config.version)
    wheel_mode = build_config.wheel_mode

    with TemporaryDirectory() as temp:
        temp_path = pathlib.Path(temp)
        if wheel_mode == "split":
            fw_wheel = make_browser_webcompy_wheel(
                get_webcompy_packge_dir(),
                temp_path,
                app_version,
            )
            app_wheel_path = make_webcompy_app_package(
                temp_path,
                get_webcompy_packge_dir(),
                build_config.app_package_path,
                app_version,
                build_config.assets,
                bundled_deps=all_bundled_deps or None,
                skip_webcompy=True,
            )
            app_wheel_filename = app_wheel_path.name
            fw_wheel_filename = fw_wheel.name
        else:
            app_wheel_path = make_webcompy_app_package(
                temp_path,
                get_webcompy_packge_dir(),
                build_config.app_package_path,
                app_version,
                build_config.assets,
                bundled_deps=all_bundled_deps or None,
            )
            app_wheel_filename = app_wheel_path.name
            fw_wheel_filename = ""

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
                if build_config.server.dev:
                    if fw_wheel_filename and filename == fw_wheel_filename:
                        headers["Cache-Control"] = "max-age=86400, must-revalidate"
                    else:
                        headers["Cache-Control"] = "no-cache"
                return Response(content, media_type=media_type, headers=headers)
            else:
                raise HTTPException(404)

        extra_wheel_filenames: list[str] | None = None
        if wheel_mode == "split":
            extra_wheel_filenames = sorted(
                f.name for f in temp_path.iterdir() if f.name.endswith(".whl") and f.name != app_wheel_filename
            )

    app_package_files_route = Route(
        "/_webcompy-app-package/{filename:path}",
        send_app_package_file,
    )

    wasm_asset_routes: list[Route] = []
    if resolved_wasm_serving == "local" and wasm_asset_files:

        async def send_wasm_asset(request: Request):
            filename: str = request.path_params.get("filename", "")  # type: ignore
            if filename in wasm_asset_files:
                asset_path = wasm_asset_files[filename]
                return FileResponse(asset_path, media_type="application/octet-stream")
            else:
                raise HTTPException(404)

        wasm_asset_routes.append(Route("/_webcompy-assets/packages/{filename:path}", send_wasm_asset))

    runtime_asset_routes: list[Route] = []
    if resolved_runtime_serving == "local" and runtime_asset_files:

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
        dev_mode=build_config.server.dev,
        prerender=True,
        app_version=app_version,
        wheel_filename=app_wheel_filename,
        pyodide_package_names=wasm_package_names + cdn_pure_python_names,
        wasm_local_urls=wasm_local_urls or None,
        lockfile_url=lockfile_url,
        runtime_serving=resolved_runtime_serving,
        extra_wheel_filenames=extra_wheel_filenames,
    )
    base_url_stripper = partial(
        re_compile("^" + re_escape("/" + app.config.base_url.strip("/"))).sub,
        "",
    )

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
                ctx = app.create_render_context(requested_path, initial_theme=initial_theme)
                try:
                    return HTMLResponse(await html_generator(ctx))
                finally:
                    ctx.dispose()
            else:
                raise HTTPException(404)

        html_route = Route("/{path:path}", send_html)
    else:

        async def send_html(request: Request):  # type: ignore
            cookie_header = request.headers.get("cookie", "")
            initial_theme = _read_initial_theme(cookie_header)
            ctx = app.create_render_context("/", initial_theme=initial_theme)
            try:
                return HTMLResponse(await html_generator(ctx))
            finally:
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

    return Starlette(routes=routes)


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

    if args.get("dev"):
        build_config.server.dev = True
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
    asgi = create_asgi_app(app, build_config)
    uvicorn.run(asgi, host="0.0.0.0", port=port, reload=build_config.server.dev)
