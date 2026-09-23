---
title: Installation
description: How to install WebComPy and set up a project with uv or Poetry.
---

# Installation

> **Note**: Until the latest release is published to PyPI, the packages are resolved from the GitHub repository via the `git+` URLs below. Once the packages are on PyPI, the install commands can be simplified (e.g. `uv add webcompy-cli` / `poetry add webcompy-cli` / `pip install webcompy[cli]`). PyScript loads `webcompy` from PyPI and does not yet support installing from a GitHub repository, so the version loaded in PyScript is the last published one.

## Prerequisites

- Python 3.12 or later.
- `uv` (recommended) or `Poetry` as the project package manager.

## Install with uv (Recommended)

Create a new project and set up dependencies using `uv`.

```bash
mkdir webcompy-project && cd webcompy-project
uv init
uv add "webcompy @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy"
uv add "webcompy-server @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-server"
uv add "webcompy-cli @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-cli"
uv run python -m webcompy init
```

## Browser dependencies

Browser dependencies are third-party packages loaded by PyScript in the browser (for example `numpy` or `matplotlib` for demos). Declare them as an optional dependency group named `browser` in `pyproject.toml` so the CLI can resolve and lock them for the PyScript runtime:

```toml
[project.optional-dependencies]
browser = ["numpy", "matplotlib"]
```

This step is optional — skip it if your app needs no third-party packages in the browser.

## Project configuration

`webcompy init` generates `webcompy_config.py`. The base shape mirrors the scaffold template:

```python
# webcompy_config.py
import app.app as app_module
from webcompy_cli.config import WebComPyBuildConfig, WebComPyServerConfig

config = WebComPyBuildConfig(
    app_module,
    dependencies=None,  # explicit browser package list (None = resolve from pyproject)
    dependencies_from=None,  # pyproject group to read browser deps from (e.g. "browser")
    server=WebComPyServerConfig(port=8080),  # dev server and SSR serving options
)
```

- `app_module`: your application package — the `WebComPyApp` instance the CLI builds and serves.
- `dependencies`: an explicit list of browser packages. Leave `None` to resolve from `pyproject.toml` instead.
- `dependencies_from`: the `pyproject.toml` group those packages are read from. Set `"browser"` to use the `[project.optional-dependencies] browser` group above.
- `server`: serving-only options such as the dev server port. It never affects the browser bundle.

When you use the `browser` group, pair it with lockfile sync so `webcompy-lock.json` tracks that group:

```python
from webcompy_cli.config import LockfileSyncConfig

config = WebComPyBuildConfig(
    app_module,
    dependencies=None,
    dependencies_from="browser",
    lockfile_sync_config=LockfileSyncConfig(sync_group="browser"),
    server=WebComPyServerConfig(port=8080),
)
```

## Lock file & dev server

Generate the lock file and start the dev server:

```bash
uv run python -m webcompy lock
uv run python -m webcompy start --dev
```

Note: `webcompy lock --install` uses `uv pip` or `pip`, not `poetry install`. Use `webcompy lock --sync` to compare versions with `pyproject.toml`.

## Install with Poetry

If you prefer Poetry, use the following setup:

```bash
poetry new webcompy-project && cd webcompy-project
poetry add "git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy"
poetry add "git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-server"
poetry add "git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-cli"
poetry run python -m webcompy init
```

Add browser dependencies to `[project.optional-dependencies]` in `pyproject.toml` (same as the uv setup above), then configure `webcompy_config.py` as shown above, and run:

```bash
poetry run python -m webcompy lock
poetry run python -m webcompy start --dev
```

Note: `webcompy lock --install` uses `uv pip` or `pip`, not `poetry install`. Use `webcompy lock --sync` to compare versions with `pyproject.toml`.
