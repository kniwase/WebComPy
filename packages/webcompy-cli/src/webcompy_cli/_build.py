from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass, field
from tempfile import TemporaryDirectory

from webcompy.app._app import WebComPyApp
from webcompy_cli._lockfile import (
    LOCKFILE_NAME,
    get_bundled_deps,
    get_cdn_pure_python_package_names,
    get_wasm_package_names,
    resolve_lockfile,
    validate_local_environment,
    verify_and_update_runtime_assets,
)
from webcompy_cli._lockfile_sync import resolve_dependencies
from webcompy_cli._pyodide_downloader import (
    PyodideDownloadError,
    download_pyodide_wheel,
    download_wasm_wheels,
    extract_wheel,
)
from webcompy_cli._pyodide_lock import PYODIDE_LOCK_URL_TEMPLATE
from webcompy_cli._runtime_downloader import RuntimeDownloadError, download_runtime_assets
from webcompy_cli._utils import (
    ensure_webcompy_modules_dir,
    generate_app_version,
    get_webcompy_packge_dir,
)
from webcompy_cli._wheel_builder import (
    make_browser_webcompy_wheel,
    make_webcompy_app_package,
)
from webcompy_cli.config._build_config import WebComPyBuildConfig
from webcompy_server import configure_server_context
from webcompy_server._html import PYSCRIPT_VERSION


@dataclass
class BuildArtifacts:
    app_version: str
    wheel_filename: str
    fw_wheel_filename: str = ""
    extra_wheel_filenames: list[str] | None = None
    pyodide_package_names: list[str] = field(default_factory=list)
    wasm_local_urls: dict[str, str] | None = None
    lockfile_url: str | None = None
    runtime_serving: str = "cdn"
    app_package_files: dict[str, tuple[bytes, str]] | None = None
    wasm_asset_files: dict[str, pathlib.Path] | None = None
    runtime_asset_files: dict[str, pathlib.Path] | None = None
    dist_dir: pathlib.Path | None = None
    dev_mode: bool = False
    cdn_temp_dir_obj: TemporaryDirectory | None = None


def resolve_build_artifacts(
    app: WebComPyApp,
    build_config: WebComPyBuildConfig,
    *,
    dev_mode: bool = False,
    dist_dir: pathlib.Path | None = None,
) -> BuildArtifacts:
    configure_server_context(app)

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

    bundled_deps = get_bundled_deps(lockfile, serve_all_deps=build_config.serve_all_deps)
    wasm_package_names = get_wasm_package_names(lockfile)

    resolved_wasm_serving = build_config.wasm_serving or "cdn"
    resolved_runtime_serving = build_config.runtime_serving or "cdn"
    base_url = app.config.base_url
    wasm_local_urls: dict[str, str] = {}
    wasm_asset_files: dict[str, pathlib.Path] = {}
    lockfile_url: str | None = None

    if resolved_wasm_serving == "local" and lockfile is not None:
        pyodide_version = lockfile.pyodide_version
        lockfile_url = PYODIDE_LOCK_URL_TEMPLATE.format(version=pyodide_version)
        downloaded_paths = download_wasm_wheels(lockfile, modules_dir)
        for name, entry in lockfile.wasm_packages.items():
            if entry.file_name and entry.sha256:
                wasm_local_urls[name] = f"{base_url}_webcompy-assets/packages/{entry.file_name}"
                if name in downloaded_paths:
                    wasm_asset_files[entry.file_name] = downloaded_paths[name]

    runtime_asset_files: dict[str, pathlib.Path] = {}
    cdn_temp_dir_obj: TemporaryDirectory | None = None
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

    with TemporaryDirectory() as _temp:
        temp_path = pathlib.Path(_temp)
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

        import mimetypes

        app_package_files: dict[str, tuple[bytes, str]] = {
            p.name: (
                p.open("rb").read(),
                mimetypes.guess_type(str(p))[0] or "application/octet-stream",
            )
            for p in temp_path.iterdir()
        }

        extra_wheel_filenames: list[str] | None = None
        if wheel_mode == "split":
            extra_wheel_filenames = sorted(
                f.name for f in temp_path.iterdir() if f.name.endswith(".whl") and f.name != app_wheel_filename
            )

    pyodide_package_names = wasm_package_names + cdn_pure_python_names

    if cdn_temp_dir_obj is not None:
        cdn_temp_dir_obj.__exit__(None, None, None)
        cdn_temp_dir_obj = None

    return BuildArtifacts(
        app_version=app_version,
        wheel_filename=app_wheel_filename,
        fw_wheel_filename=fw_wheel_filename,
        extra_wheel_filenames=extra_wheel_filenames,
        pyodide_package_names=pyodide_package_names,
        wasm_local_urls=wasm_local_urls or None,
        lockfile_url=lockfile_url,
        runtime_serving=resolved_runtime_serving,
        app_package_files=app_package_files,
        wasm_asset_files=wasm_asset_files or None,
        runtime_asset_files=runtime_asset_files or None,
        dist_dir=dist_dir,
        dev_mode=dev_mode,
        cdn_temp_dir_obj=cdn_temp_dir_obj,
    )
