from __future__ import annotations

import sys

from webcompy.cli._html import PYSCRIPT_VERSION
from webcompy.cli._lockfile import LOCKFILE_NAME, resolve_lockfile
from webcompy.cli._utils import discover_app


def lock_command() -> None:
    app, _package = discover_app()
    lockfile_path = app.config.app_package_path / LOCKFILE_NAME
    _lockfile, errors, warnings = resolve_lockfile(
        app.config.dependencies,
        PYSCRIPT_VERSION,
        lockfile_path,
    )
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if errors:
        for err in errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
    print(lockfile_path)
