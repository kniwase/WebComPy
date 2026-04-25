from __future__ import annotations

import sys

from webcompy.cli._html import PYSCRIPT_VERSION
from webcompy.cli._lockfile import LOCKFILE_NAME, generate_lockfile
from webcompy.cli._utils import discover_app


def lock_command() -> None:
    app, _package = discover_app()
    lockfile_path = app.config.app_package_path / LOCKFILE_NAME
    lockfile, errors = generate_lockfile(
        app.config.dependencies,
        PYSCRIPT_VERSION,
    )
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        sys.exit(1)
    from webcompy.cli._lockfile import save_lockfile

    save_lockfile(lockfile, lockfile_path)
    print(lockfile_path)
