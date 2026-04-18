## 1. Remove typing_extensions dependency

- [ ] 1.1 Replace `from typing_extensions import ParamSpec` with `from typing import ParamSpec` in `webcompy/reactive/_base.py`, `webcompy/aio/_aio.py`, and `webcompy/cli/_utils.py`
- [ ] 1.2 Remove `"typing_extensions"` from `dependencies` in `pyproject.toml`
- [ ] 1.3 Remove `"typing_extensions"` from the `py_packages` list in `webcompy/cli/_html.py`
- [ ] 1.4 Remove `"setuptools>=82.0.1"` and `"wheel"` from `dev` dependency group in `pyproject.toml`
- [ ] 1.5 Run `uv sync --dev --no-group docs` to verify dependency resolution works, then `uv run ruff check .` and `uv run pyright` to confirm no import errors

## 2. Implement manual wheel builder

- [ ] 2.1 Create `webcompy/cli/_wheel_builder.py` with `_discover_packages(package_dir: Path) -> list[str]` that finds all packages (directories with `__init__.py`) under the given path, replacing `setuptools.find_packages`
- [ ] 2.2 Add `_collect_package_files(package_dir: Path, packages: list[str], package_data: dict[str, list[str]] | None) -> list[tuple[Path, str]]` that collects `.py`, `.pyi`, and `py.typed` files, plus files matching `package_data` glob patterns, returning (source_path, archive_path) pairs
- [ ] 2.3 Add `_sha256_b64(data: bytes) -> str` helper that returns URL-safe base64 SHA256 hash without padding, for RECORD entries
- [ ] 2.4 Add `_write_metadata(name: str, version: str) -> str` that generates PEP 566 `METADATA` content (Metadata-Version, Name, Version)
- [ ] 2.5 Add `_write_wheel() -> str` that generates PEP 427 `WHEEL` content (Wheel-Version, Generator, Root-Is-Purelib, Tag)
- [ ] 2.6 Add `_write_record(entries: list[tuple[str, str, int]], dist_info: str) -> str` that generates the `RECORD` file content with sha256 hashes and sizes, including the RECORD entry itself with empty hash
- [ ] 2.7 Implement `make_wheel(name: str, package_dir: Path, dest: Path, version: str, package_data: dict[str, list[str]] | None = None) -> Path` that assembles all files into a ZIP archive with `.whl` extension, including the `.dist-info` directory
- [ ] 2.8 Implement `make_bundled_wheel(name: str, package_dirs: list[tuple[str, Path]], dest: Path, version: str, package_data: dict[str, list[str]] | None = None) -> Path` that merges multiple packages into a single wheel, with multiple top-level entries in `top_level.txt`

## 3. Update CLI to use bundled wheel

- [ ] 3.1 Add `package_data: dict[str, list[str]] | None = None` parameter to `WebComPyConfig.__init__` in `webcompy/cli/_config.py` and store it as an instance attribute
- [ ] 3.2 Rewrite `make_webcompy_app_package()` in `webcompy/cli/_pyscript_wheel.py` (or replace it with a function in `_wheel_builder.py`) to call `make_bundled_wheel()` instead of the old `setup()` calls, passing both `webcompy_package_dir` and the app `package_dir`, plus `package_data` from config
- [ ] 3.3 Update `webcompy/cli/_html.py`: change `py_packages` to reference a single bundled wheel URL instead of two separate wheel URLs and remove `typing_extensions`
- [ ] 3.4 Update `webcompy/cli/_server.py`: adapt the `make_webcompy_app_package` call and the wheel file serving logic to work with a single bundled wheel file
- [ ] 3.5 Update `webcompy/cli/_generate.py`: adapt the `make_webcompy_app_package` call to pass `package_data` from config, and ensure the single wheel file is placed in the output directory

## 4. Clean up and remove old code

- [ ] 4.1 Delete `from setuptools import find_packages, setup` and all `setuptools`-related logic from `webcompy/cli/_pyscript_wheel.py`, or remove the file entirely if all logic has moved to `_wheel_builder.py`
- [ ] 4.2 Remove the `external_cli_tool_wrapper` decorator from `webcompy/cli/_utils.py` if it is no longer used (it was only needed for `sys.argv` manipulation around `setup()`)
- [ ] 4.3 Update any remaining references to `_pyscript_wheel` imports to point to `_wheel_builder` if the module was renamed

## 5. Testing and verification

- [ ] 5.1 Write unit tests for `_wheel_builder.py`: test `_discover_packages`, `_collect_package_files` (with and without `package_data`), `_sha256_b64`, `make_wheel` output (valid ZIP, correct dist-info contents), and `make_bundled_wheel` output (multiple top-level packages in wheel)
- [ ] 5.2 Run the existing e2e test suite (`uv run python -m pytest tests/e2e/`) to verify browser-side behavior still works with the bundled wheel
- [ ] 5.3 Run the full test suite and lint/type checks: `uv run python -m pytest tests/`, `uv run ruff check .`, `uv run pyright`
- [ ] 5.4 Manual verification: start dev server (`uv run python -m webcompy start --dev`), verify the app loads in browser, check that `import webcompy` and the app package both work, and that `SetuptoolsDeprecationWarning` no longer appears