import os
import pathlib
import shutil
import tempfile
from functools import partial

from webcompy.app._app import WebComPyApp
from webcompy.app._config import GenerateConfig
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
from webcompy.cli._pyodide_downloader import PyodideDownloadError, download_pyodide_wheel, extract_wheel
from webcompy.cli._static_files import get_static_files
from webcompy.cli._utils import (
    discover_app,
    generate_app_version,
    get_generate_config,
    get_webcompy_packge_dir,
)
from webcompy.cli._wheel_builder import make_webcompy_app_package


def generate_static_site(app: WebComPyApp | None = None, generate_config: GenerateConfig | None = None):
    _, args = get_params()
    package = None
    if app is None:
        app_import_path = args.get("app")
        app, package = discover_app(app_import_path)
    if generate_config is None:
        generate_config = get_generate_config(package)

    serve_all_deps = args.get("serve_all_deps")
    if serve_all_deps is not None:
        app.config.serve_all_deps = serve_all_deps

    resolve_dependencies(app, lockfile_sync_config=generate_config.lockfile_sync_config)
    assert app.config.dependencies is not None

    with app.di_scope:
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

        bundled_deps = get_bundled_deps(lockfile, serve_all_deps=app.config.serve_all_deps)
        wasm_package_names = get_wasm_package_names(lockfile)

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

        all_bundled_deps = bundled_deps + cdn_extracted_deps

        dist = generate_config.dist if args.get("dist") is None else args["dist"]
        app_version = generate_app_version(app.config.version)

        dist_dir = pathlib.Path(dist).absolute()
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        os.mkdir(dist_dir)

        nojekyll_path = dist_dir / ".nojekyll"
        nojekyll_path.touch()
        print(nojekyll_path)

        if generate_config.cname:
            cname_path = dist_dir / "CNAME"
            cname_path.open("w", encoding="utf8").write(generate_config.cname)
            print(cname_path)

        static_files_dir = generate_config.static_files_dir_path.absolute()
        for relative_path in get_static_files(static_files_dir):
            src = static_files_dir / relative_path
            dst = dist_dir / relative_path
            if not (parent := dst.parent).exists():
                os.makedirs(parent)
            shutil.copy(src, dst)
            print(dst)

        scripts_dir = dist_dir / "_webcompy-app-package"
        os.mkdir(scripts_dir)
        wheel_path = make_webcompy_app_package(
            scripts_dir,
            get_webcompy_packge_dir(),
            app.config.app_package_path,
            app_version,
            app.config.assets,
            bundled_deps=all_bundled_deps or None,
        )
        wheel_filename = wheel_path.name
        for p in scripts_dir.iterdir():
            print(p)

        html_generator = partial(
            generate_html,
            app,
            False,
            True,
            app_version,
            wheel_filename,
            pyodide_package_names=wasm_package_names + cdn_pure_python_names,
        )
        if app.router_mode == "history" and app.routes:
            for p, _, _, _, page in app.routes:
                paths = (
                    {p.format(**params) for params in path_params} if (path_params := page.get("path_params")) else {p}
                )
                for path in paths:
                    if not (path_dir := dist_dir / path).exists():
                        os.makedirs(path_dir)
                    app.set_path(path)
                    html = html_generator()
                    html_path = path_dir / "index.html"
                    html_path.open("w", encoding="utf8").write(html)
                    print(html_path)
            app.set_path("//:404://")
            html = html_generator()
            html_path = dist_dir / "404.html"
            html_path.open("w", encoding="utf8").write(html)
            print(html_path)
        else:
            app.set_path("/")
            html = html_generator()
            html_path = dist_dir / "index.html"
            html_path.open("w", encoding="utf8").write(html)
            print(html_path)

        if cdn_temp_dir_obj is not None:
            cdn_temp_dir_obj.__exit__(None, None, None)

        print("done")
