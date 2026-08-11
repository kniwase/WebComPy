---
title: Installation
description: How to install WebComPy and set up a project with uv or Poetry.
---

# Installation

> **Note**: Until the latest release is published to PyPI, the packages are resolved from the GitHub repository via the `git+` URLs below. Once the packages are on PyPI, the install commands can be simplified (e.g. `uv add webcompy-cli` / `poetry add webcompy-cli` / `pip install webcompy[cli]`). PyScript loads `webcompy` from PyPI and does not yet support installing from a GitHub repository, so the version loaded in PyScript is the last published one.

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

Add browser dependencies to `[project.optional-dependencies]` in `pyproject.toml`:

```toml
[project.optional-dependencies]
browser = ["numpy", "matplotlib"]
```

Configure `webcompy_config.py` with `LockfileSyncConfig`:

```python
# webcompy_config.py
import app.app as app_module
from webcompy_cli.config import WebComPyBuildConfig, LockfileSyncConfig

config = WebComPyBuildConfig(
    app_module,
    dependencies=None,
    dependencies_from="browser",
    lockfile_sync_config=LockfileSyncConfig(sync_group="browser"),
)
```

Generate the lock file and start the dev server:

```bash
uv run python -m webcompy lock
uv run python -m webcompy start --dev
```

## Install with Poetry

If you prefer Poetry, use the following setup:

```bash
mkdir webcompy-project && cd webcompy-project
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
