## Why

The CLI wheel builder (`webcompy/cli/_pyscript_wheel.py`) calls `setuptools.setup()` directly to build Python wheels for browser deployment. This triggers `SetuptoolsDeprecationWarning` because `setup.py install` is deprecated — the project must migrate to a standards-based approach. Beyond fixing the deprecation, this change addresses three related shortcomings: the application and framework are shipped as two separate wheels (increasing browser load overhead), non-Python resources in app packages have no way to be included in wheels (they can only be served as static HTTP files), and `typing_extensions` is still listed as a runtime dependency despite Python 3.12+ making it unnecessary.

## What Changes

- **BREAKING**: Replace `setuptools`/`wheel`-based wheel building with a PEP 427-compliant manual wheel builder that constructs wheels as ZIP archives without invoking `setuptools` or `distutils`
- **BREAKING**: Bundle the webcompy framework and the user application into a single wheel by default, eliminating the separate `webcompy-*.whl` and `app-*.whl` pair
- Add `package_data` support to `WebComPyConfig` so developers can include non-Python files (JSON, CSS, HTML, etc.) inside their app package, accessible via `importlib.resources` at runtime
- Remove the `typing_extensions` runtime dependency — `typing.ParamSpec` is available in Python 3.12+ natively
- Remove `setuptools` and `wheel` from dev dependencies
- Update generated HTML to reference a single bundled wheel and remove the `typing_extensions` package reference
- Deprecate the two-wheel output path; all builds produce a single bundled wheel

## Capabilities

### New Capabilities
- `wheel-builder`: Building PEP 427-compliant Python wheels manually (no setuptools) with support for bundled packages and package_data

### Modified Capabilities
- `cli`: The CLI shall produce a single bundled wheel instead of two separate wheels, and accept package_data configuration
- `architecture`: Python packages are delivered via a single bundled wheel instead of separate framework and application wheels; typing_extensions is no longer required

## Impact

- **`webcompy/cli/_pyscript_wheel.py`**: Near-complete rewrite — remove `setuptools`/`find_packages`/`setup` imports, implement manual ZIP-based wheel building with `package_data` and bundling support
- **`webcompy/cli/_html.py`**: Update `py_packages` to reference single bundled wheel, remove `typing_extensions` reference
- **`webcompy/cli/_config.py`**: Add `package_data` field to `WebComPyConfig`
- **`webcompy/cli/_server.py`**: Adapt `make_webcompy_app_package` call for new bundled API
- **`webcompy/cli/_generate.py`**: Adapt `make_webcompy_app_package` call for new bundled API
- **`webcompy/reactive/_base.py`**: Replace `from typing_extensions import ParamSpec` with `from typing import ParamSpec`
- **`webcompy/aio/_aio.py`**: Same replacement
- **`webcompy/cli/_utils.py`**: Same replacement
- **`pyproject.toml`**: Remove `typing_extensions` from `dependencies`; remove `setuptools` and `wheel` from `dev` dependency group
- **Tests**: Update any tests referencing the two-wheel output or `typing_extensions`

## Known Issues Addressed

None directly — this change addresses a deprecation warning rather than a known issue from the issue tracker.

## Non-goals

- Changing how PyScript loads or installs wheels — we rely on PyScript's existing wheel installation mechanism
- Supporting `data_files` (files installed outside the package directory, e.g. to `/etc/`) — only `package_data` (files inside the package) is in scope
- Providing a general-purpose wheel builder library — this is internal to WebComPy's CLI
- Changing the static file serving mechanism (`static_files_dir_path`) — that remains a separate HTTP-based path for large assets
- Migrating to `pyproject.toml`-based build for the WebComPy package itself (it already uses hatchling) — this change only affects how the CLI builds wheels for browser deployment