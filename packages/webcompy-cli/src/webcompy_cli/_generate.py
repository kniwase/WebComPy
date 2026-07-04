import os
import pathlib
import shutil
import sys

import httpx

from webcompy.app._app import WebComPyApp
from webcompy_cli._argparser import get_params
from webcompy_cli._build import resolve_build_artifacts
from webcompy_cli._server import create_asgi_app
from webcompy_cli._static_files import get_static_files
from webcompy_cli._utils import discover_config
from webcompy_cli.config._build_config import WebComPyBuildConfig


async def generate_static_site(app: WebComPyApp | None = None):
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

    assert app is not None

    if args.get("dist") is not None:
        dist_dir = pathlib.Path(args["dist"]).absolute()
    else:
        dist_dir = (build_config.app_package_path / build_config.dist).absolute()
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    os.mkdir(dist_dir)

    artifacts = resolve_build_artifacts(app, build_config, dist_dir=dist_dir)

    cdn_temp_dir_obj = artifacts.cdn_temp_dir_obj
    try:
        nojekyll_path = dist_dir / ".nojekyll"
        nojekyll_path.touch()
        print(nojekyll_path)

        if build_config.cname:
            cname_path = dist_dir / "CNAME"
            cname_path.open("w", encoding="utf8").write(build_config.cname)
            print(cname_path)

        static_files_dir = (build_config.app_package_path / build_config.static_files_dir).absolute()
        for relative_path in get_static_files(static_files_dir):
            src = static_files_dir / relative_path
            dst = dist_dir / relative_path
            if not (parent := dst.parent).exists():
                os.makedirs(parent)
            shutil.copy(src, dst)
            print(dst)

        scripts_dir = dist_dir / "_webcompy-app-package"
        os.mkdir(scripts_dir)

        if artifacts.app_package_files:
            for filename, (content, _media_type) in artifacts.app_package_files.items():
                dst = scripts_dir / filename
                dst.write_bytes(content)
                print(dst)

        if artifacts.wasm_asset_files:
            wasm_assets_dir = dist_dir / "_webcompy-assets" / "packages"
            os.makedirs(wasm_assets_dir)
            for file_name, wheel_path in artifacts.wasm_asset_files.items():
                dst = wasm_assets_dir / file_name
                shutil.copy(wheel_path, dst)
                print(dst)

        if artifacts.runtime_asset_files:
            for rel_path, src_path in artifacts.runtime_asset_files.items():
                dst = dist_dir / "_webcompy-assets" / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst)
                print(dst)

        from webcompy.ui._styles import get_styles_files

        framework_ui_dir = dist_dir / "_webcompy-ui"
        framework_ui_dir.mkdir(exist_ok=True)
        for filename, content in get_styles_files().items():
            (framework_ui_dir / filename).write_bytes(content)
        print(framework_ui_dir)

        # Create ASGI app in SSG mode and fetch routes via ASGITransport
        # Note: create_asgi_app() internally configures ServerFetchPort,
        # so no separate configure() call is needed here.
        serving = create_asgi_app(app, build_config, mode="prod")

        base_url_path = app.config.base_url.strip("/")
        url_prefix = f"/{base_url_path}" if base_url_path else ""

        if app.router_mode == "history" and app.routes:
            for _, _, _, _, page in app.routes:
                if hasattr(page, "_preload"):
                    page._preload()

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=serving.asgi),
            base_url="http://test",
        ) as client:
            if app.router_mode == "history" and app.routes:
                for p, _, _, _, page in app.routes:
                    paths = (
                        {p.format(**params) for params in path_params}
                        if (path_params := page.get("path_params"))
                        else {p}
                    )
                    for path in paths:
                        response = await client.get(f"{url_prefix}/{path}")
                        if not (path_dir := dist_dir / path).exists():
                            os.makedirs(path_dir)
                        html_path = path_dir / "index.html"
                        html_path.open("w", encoding="utf8").write(response.text)
                        print(html_path)
                response = await client.get(
                    f"{url_prefix}/_webcompy_404",
                    headers={"Accept": "text/html"},
                )
                html_path = dist_dir / "404.html"
                html_path.open("w", encoding="utf8").write(response.text)
                print(html_path)
            else:
                response = await client.get(f"{url_prefix}/")
                html_path = dist_dir / "index.html"
                html_path.open("w", encoding="utf8").write(response.text)
                print(html_path)

    finally:
        if cdn_temp_dir_obj is not None:
            cdn_temp_dir_obj.__exit__(None, None, None)

    print("done")
