import os
import pathlib
import shutil
import sys
from tempfile import TemporaryDirectory

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
from webcompy.cli._pyodide_downloader import PyodideDownloadError, download_pyodide_wheel, extract_wheel
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


def generate_static_site(app: WebComPyApp | None = None):
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
    resolve_dependencies(build_config)
    assert build_config.dependencies is not None

    modules_dir = build_config.app_package_path / ".webcompy_modules"
    ensure_webcompy_modules_dir(modules_dir)

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

    bundled_deps = get_bundled_deps(lockfile, serve_all_deps=build_config.serve_all_deps)
    wasm_package_names = get_wasm_package_names(lockfile)

    resolved_wasm_serving = build_config.wasm_serving or "cdn"
    resolved_runtime_serving = build_config.runtime_serving or "cdn"
    base_url = app.config.base_url
    wasm_local_urls: dict[str, str] = {}
    wasm_wheel_paths: dict[str, pathlib.Path] = {}
    lockfile_url: str | None = None
    if resolved_wasm_serving == "local" and lockfile is not None:
        for name, entry in lockfile.wasm_packages.items():
            if entry.file_name and entry.sha256:
                try:
                    wheel_path = download_pyodide_wheel(
                        entry.file_name,
                        lockfile.pyodide_version,
                        entry.sha256,
                        modules_dir,
                    )
                except PyodideDownloadError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    sys.exit(1)
                wasm_local_urls[name] = f"{base_url}_webcompy-assets/packages/{entry.file_name}"
                wasm_wheel_paths[entry.file_name] = wheel_path
        if wasm_local_urls:
            lockfile_url = PYODIDE_LOCK_URL_TEMPLATE.format(version=lockfile.pyodide_version)

    runtime_asset_results: dict[str, tuple[pathlib.Path, str]] = {}
    cdn_temp_dir_obj = None
    try:
        if resolved_runtime_serving == "local":
            try:
                runtime_asset_results = download_runtime_assets(
                    lockfile.pyodide_version if lockfile else "0.29.3",
                    PYSCRIPT_VERSION,
                    modules_dir,
                    lock_file=lockfile,
                )
                if lockfile is not None:
                    verify_and_update_runtime_assets(
                        runtime_asset_results,
                        lockfile,
                        PYSCRIPT_VERSION,
                        build_config.app_package_path / LOCKFILE_NAME,
                    )
            except RuntimeDownloadError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
            lockfile_url = None

        cdn_pure_python_names: list[str] = []
        cdn_extracted_deps: list[tuple[str, pathlib.Path]] = []
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

        all_bundled_deps = bundled_deps + cdn_extracted_deps

        app_version = generate_app_version(build_config.version)
        wheel_mode = build_config.wheel_mode

        if args.get("dist") is not None:
            dist_dir = pathlib.Path(args["dist"]).absolute()
        else:
            dist_dir = (build_config.app_package_path / build_config.dist).absolute()
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        os.mkdir(dist_dir)

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

        extra_wheel_filenames: list[str] | None = None
        if wheel_mode == "split":
            make_browser_webcompy_wheel(
                get_webcompy_packge_dir(),
                scripts_dir,
                app_version,
            )
            wheel_path = make_webcompy_app_package(
                scripts_dir,
                get_webcompy_packge_dir(),
                build_config.app_package_path,
                app_version,
                build_config.assets,
                bundled_deps=all_bundled_deps or None,
                skip_webcompy=True,
            )
            extra_wheel_filenames = sorted(
                f.name for f in scripts_dir.iterdir() if f.name.endswith(".whl") and f.name != wheel_path.name
            )
        else:
            wheel_path = make_webcompy_app_package(
                scripts_dir,
                get_webcompy_packge_dir(),
                build_config.app_package_path,
                app_version,
                build_config.assets,
                bundled_deps=all_bundled_deps or None,
            )
        wheel_filename = wheel_path.name
        for p in scripts_dir.iterdir():
            print(p)

        if wasm_wheel_paths:
            wasm_assets_dir = dist_dir / "_webcompy-assets" / "packages"
            os.makedirs(wasm_assets_dir)
            for file_name, wheel_path in wasm_wheel_paths.items():
                dst = wasm_assets_dir / file_name
                shutil.copy(wheel_path, dst)
                print(dst)

        if runtime_asset_results:
            for rel_path, (src_path, _sha256) in runtime_asset_results.items():
                dst = dist_dir / "_webcompy-assets" / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst)
                print(dst)

        _generate_kwargs: dict[str, object] = dict(
            app_package_name=build_config.app_package_path.name,
            dev_mode=False,
            prerender=True,
            app_version=app_version,
            wheel_filename=wheel_filename,
            pyodide_package_names=wasm_package_names + cdn_pure_python_names,
            wasm_local_urls=wasm_local_urls or None,
            lockfile_url=lockfile_url,
            runtime_serving=resolved_runtime_serving,
            extra_wheel_filenames=extra_wheel_filenames,
        )
        if app.router_mode == "history" and app.routes:
            for p, _, _, _, page in app.routes:
                paths = (
                    {p.format(**params) for params in path_params} if (path_params := page.get("path_params")) else {p}
                )
                for path in paths:
                    if not (path_dir := dist_dir / path).exists():
                        os.makedirs(path_dir)
                    ctx = app.create_render_context(path)
                    html = generate_html(ctx, **_generate_kwargs)  # type: ignore[arg-type]
                    ctx.dispose()
                    html_path = path_dir / "index.html"
                    html_path.open("w", encoding="utf8").write(html)
                    print(html_path)
            ctx = app.create_render_context("//:404://")
            html = generate_html(ctx, **_generate_kwargs)  # type: ignore[arg-type]
            ctx.dispose()
            html_path = dist_dir / "404.html"
            html_path.open("w", encoding="utf8").write(html)
            print(html_path)
        else:
            ctx = app.create_render_context("/")
            html = generate_html(ctx, **_generate_kwargs)  # type: ignore[arg-type]
            ctx.dispose()
            html_path = dist_dir / "index.html"
            html_path.open("w", encoding="utf8").write(html)
            print(html_path)

    finally:
        if cdn_temp_dir_obj is not None:
            cdn_temp_dir_obj.__exit__(None, None, None)

    print("done")
