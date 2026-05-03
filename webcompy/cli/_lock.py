from __future__ import annotations

import sys

from webcompy.cli._argparser import get_params
from webcompy.cli._html import PYSCRIPT_VERSION
from webcompy.cli._lockfile import LOCKFILE_NAME, resolve_lockfile
from webcompy.cli._lockfile_sync import (
    discover_project_root,
    discover_requirements_path,
    export_requirements,
    install_requirements,
    record_requirements_path,
    resolve_dependencies,
    sync,
)
from webcompy.cli._utils import (
    discover_app,
    ensure_webcompy_modules_dir,
    get_lockfile_sync_config,
    resolve_standalone_config,
)


def lock_command() -> None:
    _, args = get_params()
    app, package = discover_app(args.get("app"))
    resolve_standalone_config(app.config)
    lockfile_sync_config = get_lockfile_sync_config(package)
    resolve_dependencies(app, lockfile_sync_config)
    assert app.config.dependencies is not None

    export_flag = args.get("export", False)
    sync_flag = args.get("sync", False)
    install_flag = args.get("install", False)

    if export_flag or sync_flag or install_flag:
        lockfile_path = app.config.app_package_path / LOCKFILE_NAME

        from webcompy.cli._lockfile import load_lockfile

        lockfile = load_lockfile(lockfile_path)
        if lockfile is None:
            print("Error: Lock file not found. Run 'webcompy lock' first.", file=sys.stderr)
            sys.exit(1)

        requirements_path = discover_requirements_path(app.config.app_package_path, lockfile_sync_config)

        if export_flag:
            export_requirements(lockfile, requirements_path)
            print(requirements_path)
            if lockfile_sync_config is None or lockfile_sync_config.requirements_path is None:
                record_requirements_path(app.config.app_package_path, requirements_path)
        elif sync_flag:
            project_root = discover_project_root(app.config.app_package_path)
            report_lines = sync(
                lockfile, project_root, lockfile_sync_config.sync_group if lockfile_sync_config else None
            )
            for line in report_lines:
                print(line)
        elif install_flag:
            install_requirements(lockfile, requirements_path)
    else:
        lockfile_path = app.config.app_package_path / LOCKFILE_NAME
        modules_dir = app.config.app_package_path / ".webcompy_modules"
        ensure_webcompy_modules_dir(modules_dir)
        _lockfile, errors, warnings = resolve_lockfile(
            app.config.dependencies,
            PYSCRIPT_VERSION,
            lockfile_path,
            modules_dir,
            wasm_serving=app.config.wasm_serving or "cdn",
            runtime_serving=app.config.runtime_serving or "cdn",
            standalone=app.config.standalone,
        )
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        if errors:
            for err in errors:
                print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)
        print(lockfile_path)
