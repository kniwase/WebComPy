import asyncio
import mimetypes
import pathlib
import tempfile
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
    get_cdn_pure_python_package_names,
    get_wasm_package_names,
    resolve_lockfile,
    validate_local_environment,
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
    discover_app,
    generate_app_version,
    get_server_config,
    get_webcompy_packge_dir,
)
from webcompy.cli._wheel_builder import make_webcompy_app_package


def create_asgi_app(
    app: WebComPyApp,
    server_config: ServerConfig | None = None,
) -> ASGIApp:
    if server_config is None:
        server_config = ServerConfig()

    resolve_dependencies(app, lockfile_sync_config=server_config.lockfile_sync_config)
    assert app.config.dependencies is not None

    lockfile, lockfile_errors, lockfile_warnings = resolve_lockfile(
        app.config.dependencies,
        PYSCRIPT_VERSION,
        app.config.app_package_path / LOCKFILE_NAME,
        wasm_serving=app.config.wasm_serving or "cdn",
        runtime_serving=app.config.runtime_serving or "cdn",
    )
    for warning in lockfile_warnings:
        print(f"Warning: {warning}", flush=True)
    for err in lockfile_errors:
        print(f"Error: {err}", flush=True)

    if lockfile is not None:
        env_errors, env_warnings = validate_local_environment(lockfile, serve_all_deps=app.config.serve_all_deps)
        for warning in env_warnings:
            print(f"Warning: {warning}", flush=True)
        for err in env_errors:
            print(f"Error: {err}", flush=True)
        lockfile_errors.extend(env_errors)

    if lockfile_errors:
        import sys

        print("Build failed due to lock file errors. Fix the above issues and try again.", file=sys.stderr)
        sys.exit(1)

    resolved_wasm_serving = app.config.wasm_serving or "cdn"

    bundled_deps = get_bundled_deps(lockfile, serve_all_deps=app.config.serve_all_deps)
    wasm_package_names = get_wasm_package_names(lockfile)

    wasm_local_urls: dict[str, str] | None = None
    lockfile_url: str | None = None
    wasm_asset_files: dict[str, tuple[bytes, str]] = {}
    if resolved_wasm_serving == "local" and lockfile is not None:
        pyodide_version = lockfile.pyodide_version
        lockfile_url = PYODIDE_LOCK_URL_TEMPLATE.format(version=pyodide_version)

        downloaded_paths = download_wasm_wheels(lockfile)
        base_url = app.config.base_url
        wasm_local_urls = {}
        for name, entry in lockfile.wasm_packages.items():
            if entry.file_name and entry.sha256:
                wasm_local_urls[name] = f"{base_url}_webcompy-assets/packages/{entry.file_name}"
                if name in downloaded_paths:
                    wheel_data = downloaded_paths[name].read_bytes()
                    media_type = "application/octet-stream"
                    wasm_asset_files[entry.file_name] = (wheel_data, media_type)

    resolved_runtime_serving = app.config.runtime_serving or "cdn"

    runtime_asset_files: dict[str, tuple[bytes, str]] = {}
    if resolved_runtime_serving == "local":
        try:
            runtime_dir = pathlib.Path(tempfile.mkdtemp())
            download_runtime_assets(
                lockfile.pyodide_version if lockfile else "0.29.3",
                PYSCRIPT_VERSION,
                runtime_dir,
            )
        except RuntimeDownloadError as e:
            import sys

            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        for asset_path in runtime_dir.rglob("*"):
            if asset_path.is_file():
                rel = asset_path.relative_to(runtime_dir)
                file_key = str(rel)
                content = asset_path.read_bytes()
                media_type = mimetypes.guess_type(str(asset_path))[0] or "application/octet-stream"
                runtime_asset_files[file_key] = (content, media_type)
        if resolved_runtime_serving == "local":
            lockfile_url = None

    cdn_pure_python_names: list[str] = []
    cdn_extracted_deps: list[tuple[str, pathlib.Path]] = []
    cdn_temp_dir_obj = None
    if not app.config.serve_all_deps:
        cdn_pure_python_names = get_cdn_pure_python_package_names(lockfile)
    elif lockfile is not None:
        for name, entry in lockfile.pure_python_packages.items():
            if entry.in_pyodide_cdn and entry.pyodide_file_name and entry.pyodide_sha256:
                try:
                    wheel_path = download_pyodide_wheel(
                        entry.pyodide_file_name,
                        lockfile.pyodide_version,
                        entry.pyodide_sha256,
                    )
                except PyodideDownloadError as e:
                    import sys

                    print(f"Error: {e}", file=sys.stderr)
                    sys.exit(1)
                if cdn_temp_dir_obj is None:
                    cdn_temp_dir_obj = tempfile.TemporaryDirectory()
                    cdn_temp_dir_obj.__enter__()
                extract_dest = pathlib.Path(cdn_temp_dir_obj.name) / name
                extract_dest.mkdir(parents=True, exist_ok=True)
                extracted = extract_wheel(wheel_path, extract_dest)
                cdn_extracted_deps.extend(extracted)

    if cdn_temp_dir_obj is not None:
        cdn_temp_dir_obj.__exit__(None, None, None)

    all_bundled_deps = bundled_deps + cdn_extracted_deps

    app_version = generate_app_version(app.config.version)

    with TemporaryDirectory() as temp:
        temp_path = pathlib.Path(temp)
        wheel_path = make_webcompy_app_package(
            temp_path,
            get_webcompy_packge_dir(),
            app.config.app_package_path,
            app_version,
            app.config.assets,
            bundled_deps=all_bundled_deps or None,
        )
        wheel_filename = wheel_path.name
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
            if server_config.dev and filename == wheel_filename:
                headers["Cache-Control"] = "no-cache"
            return Response(content, media_type=media_type, headers=headers)
        else:
            raise HTTPException(404)

    app_package_files_route = Route(
        "/_webcompy-app-package/{filename:path}",
        send_app_package_file,
    )

    wasm_asset_routes: list[Route] = []
    if resolved_wasm_serving == "local" and wasm_asset_files:

        async def send_wasm_asset(request: Request):
            filename: str = request.path_params.get("filename", "")  # type: ignore
            if filename in wasm_asset_files:
                content, media_type = wasm_asset_files[filename]
                return Response(content, media_type=media_type)
            else:
                raise HTTPException(404)

        wasm_asset_routes.append(Route("/_webcompy-assets/packages/{filename:path}", send_wasm_asset))

    runtime_asset_routes: list[Route] = []
    if resolved_runtime_serving == "local" and runtime_asset_files:

        async def send_runtime_asset(request: Request):
            filename: str = request.path_params.get("filename", "")  # type: ignore
            if filename in runtime_asset_files:
                content, media_type = runtime_asset_files[filename]
                return Response(content, media_type=media_type)
            else:
                raise HTTPException(404)

        runtime_asset_routes.append(Route("/_webcompy-assets/{filename:path}", send_runtime_asset))

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
        wheel_filename,
        pyodide_package_names=wasm_package_names + cdn_pure_python_names,
        wasm_local_urls=wasm_local_urls or None,
        lockfile_url=lockfile_url,
        runtime_serving=resolved_runtime_serving,
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

    routes: list[Route] = [
        *dev_routes,
        app_package_files_route,
        *wasm_asset_routes,
        *runtime_asset_routes,
        *static_file_routes,
        html_route,
    ]

    return Starlette(routes=routes)


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
    serve_all_deps = args.get("serve_all_deps")
    if serve_all_deps is not None:
        app.config.serve_all_deps = serve_all_deps
    wasm_serving = args.get("wasm_serving")
    if wasm_serving is not None:
        app.config.wasm_serving = wasm_serving
    runtime_serving = args.get("runtime_serving")
    if runtime_serving is not None:
        app.config.runtime_serving = runtime_serving
    port = args.get("port") or server_config.port
    asgi = create_asgi_app(app, server_config)
    uvicorn.run(asgi, host="0.0.0.0", port=port, reload=server_config.dev)
