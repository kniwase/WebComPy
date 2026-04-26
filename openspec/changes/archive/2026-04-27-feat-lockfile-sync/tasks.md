# Tasks: Lock File Sync — Bidirectional Version Synchronization

## Context

This change adds three sub-commands to `webcompy lock`: `--export`, `--sync`, and `--install`. It also changes `AppConfig.dependencies` from `list[str]` (default `[]`) to `list[str] | None` (default `None`) with auto-population from `pyproject.toml`. The change relies on auto-discovery of the project root (via `pyproject.toml`), a new `LockfileSyncConfig` dataclass in `webcompy_server_config.py`, and a new module `webcompy/cli/_lockfile_sync.py`.

### Key files to reference during implementation

- `webcompy/cli/_lockfile.py` — `Lockfile`, `PyodidePackageEntry`, `BundledPackageEntry`, `load_lockfile`, `save_lockfile` data structures and functions
- `webcompy/cli/_lock.py` — current `lock_command()` (24 lines, to be extended)
- `webcompy/cli/_argparser.py` — `get_params()` with sub-commands (lock sub-parser at line 63)
- `webcompy/cli/_utils.py` — `discover_app()`, `get_server_config()`, `get_generate_config()` (pattern for config discovery)
- `webcompy/cli/_exception.py` — `WebComPyCliException`
- `webcompy/app/_config.py` — `AppConfig`, `ServerConfig`, `GenerateConfig` dataclasses (add `LockfileSyncConfig` here, change `AppConfig.dependencies`)
- `webcompy/cli/template_data/webcompy_server_config.py` — template for `webcompy init` (DO NOT add `lockfile_sync_config` to this template — it's optional/auto-discovered)
- `webcompy/cli/template_data/webcompy_config.py` — template for `webcompy init` (update `dependencies` default to `None`)
- `openspec/changes/feat-lockfile-sync/design.md` — full design document

### Key design decisions

1. **No `--path` flag** — all paths are auto-discovered or configured via `LockfileSyncConfig.requirements_path`
2. **`--sync`** replaces `--sync-from SOURCE` — auto-discovers both `requirements.txt` and `pyproject.toml`
3. **`LockfileSyncConfig`** is stored in `webcompy_server_config.py` — follows same pattern as `ServerConfig`/`GenerateConfig`
4. **Project root discovery** walks up from `app_package_path` until `pyproject.toml` is found — this is the hard boundary
5. **`packaging` library is NOT available** — PEP 508 parsing must use `tomllib` + regex, not `packaging.requirements.Requirement`
6. **Python 3.12+** — `tomllib` is available in the standard library
7. **`uv pip` is preferred over `pip`** — checked via `shutil.which("uv")`
8. **WASM packages are excluded from export** — only `bundled_packages` and non-WASM `pyodide_packages` are included (WebComPy is SSR/SSG-only, so non-WASM packages need local installation)
9. **`sync_group`** selects `[project.optional-dependencies.{sync_group}]` from `pyproject.toml`; when `None`, uses `[project.dependencies]`
10. **`AppConfig.dependencies` defaults to `None`** — when `None`, auto-populate from `pyproject.toml` using `dependencies_from`; explicit lists bypass auto-population (backward compatible)
11. **Version specifiers are stripped** from `pyproject.toml` entries when populating `AppConfig.dependencies` — version pinning is handled by `webcompy-lock.json`

---

- [x] **Task 1: Add `LockfileSyncConfig`, change `AppConfig.dependencies`, and add project root discovery**

**Estimated time: ~2 hours**

### Steps

1. Modify `webcompy/app/_config.py`:

   a. Change `AppConfig.dependencies` from `list[str] = field(default_factory=list)` to `list[str] | None = None`.

   b. Add `dependencies_from: str | None = None` field to `AppConfig`:
      ```python
      @dataclass
      class AppConfig:
          app_package: Path | str = "."
          base_url: str = "/"
          dependencies: list[str] | None = None       # None = auto-populate from pyproject.toml
          dependencies_from: str | None = None        # pyproject.toml group key, None = [project.dependencies]
          assets: dict[str, str] | None = None
          version: str | None = None
          profile: bool = False
          hydrate: bool = True
      ```

   c. Add `LockfileSyncConfig` dataclass:
      ```python
      @dataclass
      class LockfileSyncConfig:
          requirements_path: str | None = None
          sync_group: str | None = None
      ```
      Place it after `GenerateConfig`.

2. Create `webcompy/cli/_lockfile_sync.py` with the following functions:

   a. `discover_project_root(app_package_path: pathlib.Path) -> pathlib.Path`:
      - Iterate `app_package_path.parents` (including `app_package_path` itself — check it first).
      - For each directory, check if `(dir / "pyproject.toml").exists()`.
      - Return the first directory where `pyproject.toml` exists.
      - If no `pyproject.toml` is found after checking all parents, raise `WebComPyCliException` with message: `"Could not find pyproject.toml above {app_package_path}. Set LockfileSyncConfig.requirements_path in webcompy_server_config.py."`

   b. `discover_requirements_path(app_package_path: pathlib.Path, lockfile_sync_config: LockfileSyncConfig | None = None) -> pathlib.Path`:
      - If `lockfile_sync_config` is not None and `lockfile_sync_config.requirements_path` is not None:
        - Resolve the path: if it's absolute, use as-is; if relative, resolve relative to `app_package_path`.
        - Return the resolved `Path`.
      - Otherwise, call `discover_project_root(app_package_path)` to get `project_root`.
      - Return `project_root / "requirements.txt"`.

3. Add `get_lockfile_sync_config(package: str | None = None) -> LockfileSyncConfig` to `webcompy/cli/_utils.py`:
   - Follow the exact same pattern as `get_server_config()` and `get_generate_config()`.
   - Import `LockfileSyncConfig` from `webcompy.app._config`.
   - For each prefix (package-level first, then root-level), import `webcompy_server_config` and try `getattr(module, "lockfile_sync_config", None)`.
   - If found and is `LockfileSyncConfig` instance, return it.
   - If not found, return `LockfileSyncConfig()`.
   - Add appropriate error if the attribute exists but is wrong type.

4. Write unit tests in `tests/test_lockfile_sync.py`:

   a. `TestDiscoverProjectRoot`:
      - Test: `pyproject.toml` in parent → returns parent dir
      - Test: `pyproject.toml` in grandparent → returns grandparent dir
      - Test: `pyproject.toml` in app_package_path itself → returns app_package_path
      - Test: No `pyproject.toml` anywhere → raises `WebComPyCliException`
      - Test: Multiple `pyproject.toml` in hierarchy → returns nearest (closest to app_package_path)

   b. `TestDiscoverRequirementsPath`:
      - Test: `LockfileSyncConfig(requirements_path="../requirements.txt")` → resolves relative to app_package_path
      - Test: `LockfileSyncConfig(requirements_path="/absolute/path/requirements.txt")` → uses absolute path
      - Test: `LockfileSyncConfig(requirements_path=None)` → auto-discovers via project root
      - Test: `LockfileSyncConfig()` (defaults) → auto-discovers

   c. `TestGetLockfileSyncConfig`:
      - Test: config file with `lockfile_sync_config = LockfileSyncConfig(sync_group="browser")` → returns config
      - Test: config file without `lockfile_sync_config` → returns `LockfileSyncConfig()`
      - Test: missing config file → returns `LockfileSyncConfig()`

### Acceptance Criteria

- `discover_project_root()` finds the nearest `pyproject.toml` ancestor directory.
- `discover_project_root()` raises `WebComPyCliException` when no `pyproject.toml` is found.
- `discover_requirements_path()` returns explicit path when `LockfileSyncConfig.requirements_path` is set.
- `discover_requirements_path()` falls back to auto-discovery when `requirements_path` is `None`.
- `get_lockfile_sync_config()` returns a `LockfileSyncConfig` instance (from config file or default).
- All unit tests pass.

---

- [x] **Task 2: Implement `export_requirements()` and path recording**

**Estimated time: ~1 hour**

### Steps

1. Implement `export_requirements(lockfile: Lockfile, path: pathlib.Path) -> None` in `webcompy/cli/_lockfile_sync.py`:
   - Collect entries from `lockfile.bundled_packages` (all entries) and `lockfile.pyodide_packages` (only `is_wasm=False` entries).
   - Sort entries alphabetically by package name (case-insensitive).
   - Format each entry as `{name}=={version}` (one per line).
   - Write a header comment: `# Generated by webcompy lock --export` as the first line, followed by a blank line, then the entries.
   - Create parent directories if needed: `path.parent.mkdir(parents=True, exist_ok=True)`.
   - Write to `path` with UTF-8 encoding.

2. Implement `record_requirements_path(app_package_path: pathlib.Path, requirements_path: pathlib.Path, config_module_path: pathlib.Path | None = None) -> None`:
   - Calculate the relative path from `app_package_path` to `requirements_path`: `requirements_path.relative_to(app_package_path)` or `os.path.relpath()`.
   - If `config_module_path` is None, search for `webcompy_server_config.py` using the same discovery pattern as `get_server_config()` (package-level first, then root-level).
   - Parse the file and check if `lockfile_sync_config` is already defined.
   - If not defined, append: `from webcompy.app._config import LockfileSyncConfig` (if not already imported) and `lockfile_sync_config = LockfileSyncConfig(requirements_path="{relative_path}")`.
   - If `lockfile_sync_config` exists but `requirements_path` is None, update it to set `requirements_path`.
   - Use `ast` module to parse the Python source file and find the insertion point (preserve formatting).
   - **Important**: This function modifies a user's source file. Use a conservative approach: if parsing/ modification fails, print a warning and suggest the user manually add the config.

3. Write unit tests in `tests/test_lockfile_sync.py`:

   a. `TestExportRequirements`:
      - Test: lockfile with `bundled_packages` only → all entries exported.
      - Test: lockfile with `pyodide_packages` (WASM and non-WASM) → non-WASM included, WASM excluded.
      - Test: entries sorted alphabetically.
      - Test: header comment present.
      - Test: empty lockfile → only header comment and blank line.
      - Test: parent directory creation (write to `tmp_path / "sub" / "dir" / "requirements.txt"`).

   b. `TestRecordRequirementsPath`:
      - Test: config file without `lockfile_sync_config` → adds import and config line.
      - Test: config file with existing `lockfile_sync_config(requirements_path=None)` → updates `requirements_path`.
      - Test: config file with existing `lockfile_sync_config(requirements_path="../requirements.txt")` → no change (already set).
      - Test: relative path correctness (app_package `/home/user/project/my_app/`, requirements `/home/user/project/requirements.txt` → `../requirements.txt`).

### Acceptance Criteria

- Exported `requirements.txt` contains pinned versions for all bundled and non-WASM Pyodide packages.
- WASM packages are excluded.
- Entries are sorted alphabetically.
- Header comment is present.
- Parent directories are created.
- Discovered path is recorded in `webcompy_server_config.py` on first export (if not already set).

---

- [x] **Task 3: Implement `sync_from_requirements_txt()` and `sync_from_pyproject_toml()`**

**Estimated time: ~1.5 hours**

### Steps

1. Implement `sync_from_requirements_txt(lockfile: Lockfile, path: pathlib.Path) -> list[str]` in `webcompy/cli/_lockfile_sync.py`:
   - Read `path` as UTF-8 text.
   - Parse each line: strip whitespace, skip empty lines and lines starting with `#`.
   - For each line, try to match the pattern `{name}=={version}` (regex: `^([a-zA-Z0-9_.-]+)==([a-zA-Z0-9_.+!-]+)$`).
   - Lines that don't match `==` are reported as informational (unpinned or non-standard format).
   - Build a dict of lockfile packages: combine `bundled_packages` (all) and `pyodide_packages` (only `is_wasm=False`), mapping `name.lower().replace("-", "_")` → `(name, version)`.
   - For each parsed entry:
     - If name matches and version matches: report `✓ {name}: {version} (matches)`.
     - If name matches but version differs: report `⚠ {name}: lock={lock_version}, requirements.txt={req_version} (mismatch) Suggest: pip install {name}=={lock_version}`.
     - If name not in lockfile: report `ℹ {name}: not in lock file (non-browser dependency?)`.
     - If name is in lockfile but only as WASM package (not in the dict): report `ℹ {name}: WASM package, not applicable for local install`.
   - Return sorted list of report lines.

2. Implement `sync_from_pyproject_toml(lockfile: Lockfile, path: pathlib.Path, sync_group: str | None = None) -> list[str]`:
   - Read and parse `path` using `tomllib.open(path, "rb")` (Python 3.12+, `tomllib` is in stdlib).
   - If `sync_group` is None:
     - Read `[project][dependencies]` from the parsed TOML. If the key doesn't exist, return `["ℹ No [project.dependencies] found in pyproject.toml"]`.
     - The value is a list of PEP 508 dependency strings (e.g., `"markupsafe>=2.0"`, `"requests==2.32.4"`).
   - If `sync_group` is set:
     - Read `[project.optional-dependencies][{sync_group}]` from the parsed TOML.
     - If `[project.optional-dependencies]` doesn't exist, return `["⚠ No [project.optional-dependencies] found in pyproject.toml"]`.
     - If the sync_group key doesn't exist, return `["⚠ No [project.optional-dependencies.{sync_group}] found in pyproject.toml"]`.
   - For each dependency string, parse it:
     - Try regex pattern `^([a-zA-Z0-9_.-]+)==([a-zA-Z0-9_.+!-]+)$` for pinned (`==`).
     - Try regex pattern `^([a-zA-Z0-9_.-]+)([><=!~].+)$` for version ranges.
     - Try regex pattern `^([a-zA-Z0-9_.-]+)$` for bare package names.
     - For pinned entries (`==`): compare version with lockfile (same logic as requirements.txt sync).
     - For version range entries: report `ℹ {name}: not pinned ("{specifier}"), lock file has {lock_version} Suggest: pin to {name}=={lock_version}`.
     - For bare names: report `ℹ {name}: no version specifier, lock file has {lock_version}`.
   - Return sorted list of report lines.

3. Implement `sync(lockfile: Lockfile, project_root: pathlib.Path, sync_group: str | None = None) -> list[str]`:
   - Check if `(project_root / "requirements.txt").exists()`. If yes, call `sync_from_requirements_txt()`.
   - Check if `(project_root / "pyproject.toml").exists()`. If yes, call `sync_from_pyproject_toml()`.
   - If neither exists, return `["⚠ No requirements.txt or pyproject.toml found at {project_root}"]`.
   - Combine and return all report lines.

4. Write unit tests in `tests/test_lockfile_sync.py`:

   a. `TestSyncFromRequirementsTxt`:
      - Test: All matching entries → all `✓`.
      - Test: Version mismatch → `⚠` with suggestion.
      - Test: Extra entry not in lockfile → `ℹ`.
      - Test: WASM package in requirements.txt → `ℹ` (not applicable).
      - Test: Non-`==` specifiers (e.g., `>=`) → informational note.

   b. `TestSyncFromPyprojectToml`:
      - Test: All pinned entries in `[project.dependencies]` → all `✓`.
      - Test: Unpinned entries (`>=`) → suggestion to pin.
      - Test: Bare package names → informational note.
      - Test: `sync_group="browser"` → reads from `[project.optional-dependencies.browser]`.
      - Test: `sync_group="browser"` but key doesn't exist → `⚠` warning.
      - Test: `[project.dependencies]` missing → informational message.
      - Test: Invalid `pyproject.toml` → error reported.

   c. `TestSync`:
      - Test: Both files exist → combines reports.
      - Test: Only `pyproject.toml` exists → only TOML report.
      - Test: Neither file exists → warning.

### Acceptance Criteria

- Matching versions reported as `✓`.
- Mismatched versions reported with both versions and a suggested fix command.
- Extra entries (not in lockfile) reported as informational.
- WASM packages in requirements.txt reported as not applicable.
- Non-`==` specifiers reported with a note.
- `sync_group` routes to `[project.optional-dependencies.{sync_group}]`.
- Missing group key reported as `⚠` warning.
- Parsing uses `tomllib` (stdlib) for TOML and regex for PEP 508 parsing (no `packaging` import).

---

- [x] **Task 4: Implement `install_requirements()`**

**Estimated time: ~0.5 hours**

### Steps

1. Implement `install_requirements(lockfile: Lockfile, requirements_path: pathlib.Path) -> None` in `webcompy/cli/_lockfile_sync.py`:
   - Call `export_requirements(lockfile, requirements_path)` to generate the requirements file.
   - Check `shutil.which("uv")`:
     - If `uv` is found: run `uv pip install -r {requirements_path}` via `subprocess.run(["uv", "pip", "install", "-r", str(requirements_path)])`.
     - If `uv` is not found: run `sys.executable -m pip install -r {requirements_path}` via `subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_path)])`.
   - If the subprocess returns a non-zero exit code, call `sys.exit(result.returncode)`.
   - Print the subprocess stdout/stderr to the user.

2. Write unit tests in `tests/test_lockfile_sync.py`:

   a. `TestInstallRequirements`:
      - Test: `uv` available → runs `uv pip install -r {path}`.
      - Test: `uv` not available → runs `{sys.executable} -m pip install -r {path}`.
      - Test: Install command exit code is propagated (mock `subprocess.run` to return exit code 1).
      - Test: `export_requirements` is called before install (verify the file exists).
      - Use `monkeypatch` to mock `shutil.which`, `subprocess.run`, and `export_requirements`.

### Acceptance Criteria

- `install_requirements()` generates a requirements file via `export_requirements()`, then runs the install command.
- `uv pip install` is used when `uv` is available.
- `sys.executable -m pip install` is used as fallback.
- The install command's exit code is propagated via `sys.exit()`.

---

- [x] **Task 5: Extend `webcompy lock` CLI with `--export`, `--sync`, and `--install` flags**

**Estimated time: ~1 hour**

### Steps

1. Modify `webcompy/cli/_argparser.py`:
   - Add three mutually exclusive flags to the `lock` sub-parser:
     - `parser_lock.add_argument("--export", action="store_true", help="Export lock file dependencies to requirements.txt")`
     - `parser_lock.add_argument("--sync", action="store_true", help="Compare lock file with requirements.txt/pyproject.toml")`
     - `parser_lock.add_argument("--install", action="store_true", help="Export and install lock file dependencies")`
   - After the sub-parser definitions, add mutual exclusion validation:
     - If both `--export` and `--sync`, or `--export` and `--install`, or `--sync` and `--install` are present, use `parser.error()` to report mutual exclusion. (Consider using `add_mutually_exclusive_group()` on the sub-parser.)

2. Modify `webcompy/cli/_lock.py`:
   - Import: `from webcompy.cli._lockfile_sync import (export_requirements, sync, install_requirements, discover_requirements_path, discover_project_root)`, `from webcompy.cli._utils import discover_app, get_lockfile_sync_config`, `from webcompy.cli._lockfile import load_lockfile, LOCKFILE_NAME`.
   - In `lock_command()`, after `discover_app()`, check the flags:
     ```python
     export_flag = args.get("export", False)
     sync_flag = args.get("sync", False)
     install_flag = args.get("install", False)
     
     if export_flag or sync_flag or install_flag:
         lockfile_path = app.config.app_package_path / LOCKFILE_NAME
         lockfile = load_lockfile(lockfile_path)
         if lockfile is None:
             print("Error: Lock file not found. Run 'webcompy lock' first.", file=sys.stderr)
             sys.exit(1)
         lockfile_sync_config = get_lockfile_sync_config(package)
         requirements_path = discover_requirements_path(app.config.app_package_path, lockfile_sync_config)
         
         if export_flag:
             export_requirements(lockfile, requirements_path)
             print(requirements_path)
         elif sync_flag:
             project_root = discover_project_root(app.config.app_package_path)
             report_lines = sync(lockfile, project_root, lockfile_sync_config.sync_group if lockfile_sync_config else None)
             for line in report_lines:
                 print(line)
         elif install_flag:
             install_requirements(lockfile, requirements_path)
     else:
         # Existing lock generation code
     ```
   - After `export_flag` successfully writes `requirements.txt`, call `record_requirements_path()` if this is the first run (i.e., `lockfile_sync_config.requirements_path is None`).

3. Write unit tests for argument parsing in `tests/test_lockfile_sync.py`:

   a. `TestLockArgParser`:
      - Test: `webcompy lock --export` → `export=True, sync=False, install=False`.
      - Test: `webcompy lock --sync` → `export=False, sync=True, install=False`.
      - Test: `webcompy lock --install` → `export=False, sync=False, install=True`.
      - Test: `webcompy lock` (no flags) → `export=False, sync=False, install=False`.
      - Test: `webcompy lock --export --sync` → parser error.
      - Test: `webcompy lock --export --install` → parser error.
      - Test: `webcompy lock --sync --install` → parser error.

### Acceptance Criteria

- `webcompy lock --export` runs the export operation.
- `webcompy lock --sync` runs the comparison operation.
- `webcompy lock --install` runs the install operation.
- Combining any two of `--export`, `--sync`, `--install` reports a mutual exclusion error.
- Default `webcompy lock` (no flags) still generates/updates the lock file.
- Missing lock file produces a clear error message for all three sub-commands.

---

- [x] **Task 6: Update unit tests, update home page setup guide, and verify**

**Estimated time: ~1.5 hours**

### Steps

1. Run all existing tests: `uv run python -m pytest tests/ --tb=short`.
2. Run lint: `uv run ruff check .`.
3. Run type check: `uv run pyright`.
4. Fix any issues found by lint/typecheck/test.

5. Update the site home page at `docs_src/templates/home.py` to rewrite the "Get started" section with uv/poetry-based setup flows instead of the original plain `pip install` approach. The updated sections shall contain:

    **Section: Get started with uv (Recommended)**

    - Commands: `uv init` → `uv add webcompy` → `uv run python -m webcompy init`
    - Example `pyproject.toml` `[project.optional-dependencies] browser = ["numpy", "matplotlib"]`
    - Example `webcompy_config.py` with `dependencies=None, dependencies_from="browser"` and `webcompy_server_config.py` with `LockfileSyncConfig(sync_group="browser")`
    - Generate lock file and start dev server: `webcompy lock` → `webcompy start --dev`

    **Section: Get started with Poetry**

    - Commands: `poetry new` → `poetry add webcompy` → `poetry run python -m webcompy init`
    - Same `pyproject.toml` `[project.optional-dependencies]` configuration as uv
    - Note that `webcompy lock --install` uses `uv pip` or `pip`, not `poetry install`. Use `webcompy lock --sync` to compare versions.
    - Generate lock file and start dev server: `webcompy lock` → `webcompy start --dev`

    **Section: Lock File Commands**

    - Reference table with `webcompy lock`, `--export`, `--sync`, `--install` commands and their descriptions

### Acceptance Criteria

- All existing tests pass.
- All new tests pass.
- Lint passes (`ruff check .`).
- Type check passes (`pyright`).
- Documentation page covers `uv` and `poetry` setup examples with copy-paste configuration.
- Documentation page explains auto-discovery and `LockfileSyncConfig`.

---

- [x] **Task 7: Implement `AppConfig.dependencies` auto-population from `pyproject.toml`**

**Estimated time: ~1.5 hours**

### Steps

1. Add `resolve_dependencies(app: WebComPyApp) -> None` function to `webcompy/cli/_lockfile_sync.py`:

   a. If `app.config.dependencies is not None`, return immediately (explicit list takes precedence, backward compatible).

   b. Call `discover_project_root(app.config.app_package_path)` to find `pyproject.toml`. If not found, raise `WebComPyCliException`: `"Could not find pyproject.toml above {app_package_path}. Set AppConfig.dependencies explicitly or ensure pyproject.toml exists."`

   c. Parse `pyproject.toml` using `tomllib`:
      - If `app.config.dependencies_from` is `None`: Read `[project][dependencies]` list.
      - If `app.config.dependencies_from` is set (e.g., `"browser"`): Read `[project.optional-dependencies][{dependencies_from}]` list.
      - If the specified section or key doesn't exist, raise `WebComPyCliException` with a clear message.

   d. For each dependency string, strip version specifiers to extract package names only:
      - Regex: `^([a-zA-Z0-9_.-]+)` — capture the package name (everything before version specifier characters like `==`, `>=`, `<=`, `~=`, `!=`, `;`, whitespace, or end of string).
      - Example: `"flask>=3.0"` → `"flask"`, `"numpy==2.2.5"` → `"numpy"`, `"click"` → `"click"`.
   
   e. Set `app.config.dependencies = [extracted_names]`.

   f. If `dependencies_from` and `sync_group` (from `LockfileSyncConfig`) are both set and differ, print a warning: `⚠ AppConfig.dependencies_from="{dependencies_from}" differs from LockfileSyncConfig.sync_group="{sync_group}"`. This is only a warning, not an error — the user may intentionally use different groups.

2. Call `resolve_dependencies(app)` in all CLI command paths that use `app.config.dependencies`:
   - `webcompy/cli/_lock.py` — at the beginning of `lock_command()`, before `resolve_lockfile()`.
   - `webcompy/cli/_server.py` — at the beginning of `create_asgi_app()`, before `resolve_lockfile()`.
   - `webcompy/cli/_generate.py` — at the beginning of `generate_static_site()`, before `resolve_lockfile()`.
   
   Note: `resolve_dependencies()` must be called regardless of whether `--export`, `--sync`, or `--install` flags are used, because all paths need `app.config.dependencies` to be populated.

3. Update existing call sites that currently expect `dependencies: list[str]` to handle `list[str] | None`:
   - `webcompy/cli/_lockfile.py` — `generate_lockfile()` and `resolve_lockfile()` accept `dependencies: list[str]`. After `resolve_dependencies()`, `app.config.dependencies` is guaranteed to be `list[str]` (either the original explicit list, or the auto-populated list). Use `assert` or type narrowing to satisfy type checkers.
   - `webcompy/cli/_dependency_resolver.py` — `classify_dependencies()` accepts `dependencies: list[str]`. No change needed since `app.config.dependencies` will always be `list[str]` after resolution.

4. Update `webcompy/cli/template_data/webcompy_config.py` to use `dependencies=None`:
   ```python
   app_config = AppConfig(app_package=Path(__file__).parent / "app", base_url="/")
   ```
   Remove the explicit `dependencies=[]` if it was there (it's now `None` by default).

5. Update `docs_src/webcompy_config.py` to use `dependencies_from="browser"` or `dependencies=None` as appropriate for the docs site. The docs site depends on `numpy` and `matplotlib`, which are listed in `docs_src/webcompy-lock.json`. Since there is no `pyproject.toml` in `docs_src/`, keep the explicit list: `dependencies=["numpy", "matplotlib"]`.

6. Fix existing tests that broke due to the `dependencies` default change:
   - `tests/test_config_dataclasses.py`: Update the test that checks `config.dependencies == []` to check `config.dependencies is None`.
   - `tests/test_app_instance.py`: Update the test that checks `app.config.dependencies == []` to check `app.config.dependencies is None`.
   - Any test that creates `AppConfig()` expecting `dependencies=[]` must now use `AppConfig(dependencies=[])` if they need an empty list, or rely on `None`.
   - Tests that create `AppConfig(dependencies=["numpy"])` are unaffected (explicit list).

7. Add unit tests for `resolve_dependencies()`:

   a. Test: `dependencies=None, dependencies_from=None` → reads `[project.dependencies]` from `pyproject.toml`.
   b. Test: `dependencies=None, dependencies_from="browser"` → reads `[project.optional-dependencies.browser]`.
   c. Test: `dependencies=["numpy"]` (explicit) → no `pyproject.toml` reading, uses explicit list.
   d. Test: `dependencies=None` but no `pyproject.toml` → raises `WebComPyCliException`.
   e. Test: `dependencies_from="nonexistent"` but key doesn't exist in `[project.optional-dependencies]` → raises `WebComPyCliException`.
   f. Test: Version specifiers are stripped (`"flask>=3.0"` → `"flask"`, `"numpy==2.2.5"` → `"numpy"`).
   g. Test: `dependencies_from="browser"` differs from `sync_group="deps"` → warning printed.

### Acceptance Criteria

- `AppConfig.dependencies` defaults to `None`.
- When `None` and `dependencies_from` is set, dependencies are auto-populated from `pyproject.toml`.
- When `None` and `dependencies_from` is `None`, dependencies are auto-populated from `[project.dependencies]`.
- Explicit `dependencies` list (non-None) bypasses `pyproject.toml` reading entirely.
- Version specifiers are stripped from `pyproject.toml` entries.
- Mismatch between `dependencies_from` and `sync_group` produces a warning.
- All existing tests pass after updating default expectations.
- Template and docs source configs are updated appropriately.

---

- [x] **Task 8: Configure docs_src as a uv-managed project with dependencies_from**

**Estimated time: ~1 hour**

### Context

Currently, `docs_src/webcompy_config.py` has `dependencies=["numpy", "matplotlib"]` (explicit list). The root `pyproject.toml` has these in `[dependency-groups] docs`. The goal is to convert `docs_src/` to a self-contained uv project with its own `pyproject.toml`, so that `dependencies_from` can resolve browser dependencies without manual duplication.

### Current State

```
WebComPy/
├── pyproject.toml              ← root project (webcompy framework)
│   [dependency-groups]
│   docs = ["numpy==2.2.5", "matplotlib>=3.9.0,<4"]
│
├── docs_src/
│   ├── webcompy_config.py      ← dependencies=["numpy", "matplotlib"] (manual)
│   ├── webcompy-lock.json      ← auto-generated
│   └── (no pyproject.toml)
```

### Target State

```
WebComPy/
├── pyproject.toml              ← root project (unchanged)
│   [dependency-groups]
│   docs = ["numpy==2.2.5", "matplotlib>=3.9.0,<4"]  ← still useful for uv sync at root
│
├── docs_src/
│   ├── pyproject.toml          ← NEW: uv project for docs_src
│   │   [project]
│   │   name = "webcompy-docs"
│   │   version = "0.0.0"
│   │   dependencies = []        ← browser deps are in optional-dependencies
│   │   [project.optional-dependencies]
│   │   browser = ["numpy", "matplotlib"]
│   │
│   ├── webcompy_config.py      ← dependencies=None, dependencies_from="browser"
│   ├── webcompy_server_config.py ← lockfile_sync_config=LockfileSyncConfig(sync_group="browser")
│   ├── webcompy-lock.json      ← auto-regenerated after config change
│   └── (no uv.lock needed — lock is in webcompy-lock.json)
```

### Steps

1. Create `docs_src/pyproject.toml`:
   ```toml
   [project]
   name = "webcompy-docs"
   version = "0.0.0"
   requires-python = ">=3.12"
   dependencies = []

   [project.optional-dependencies]
   browser = ["numpy", "matplotlib"]
   ```
   Note: `version = "0.0.0"` is a placeholder — this project exists only for dependency metadata, not for publishing. The version specifiers in `browser` are intentionally unpinned because `webcompy-lock.json` handles pinning.

2. Update `docs_src/webcompy_config.py`:
   ```python
   from pathlib import Path
   from webcompy.app import AppConfig

   app_import_path = "docs_src.bootstrap:app"
   app_config = AppConfig(
       app_package=Path(__file__).parent,
       base_url="/",
       dependencies=None,
       dependencies_from="browser",
   )
   ```

3. Update `docs_src/webcompy_server_config.py`:
   ```python
   from webcompy.app._config import GenerateConfig, LockfileSyncConfig, ServerConfig

   server_config = ServerConfig(port=8080, dev=False)
   generate_config = GenerateConfig(dist="docs", cname="webcompy.net")
   lockfile_sync_config = LockfileSyncConfig(sync_group="browser")
   ```

4. Regenerate `docs_src/webcompy-lock.json` by running `uv run python -m webcompy lock --app docs_src.bootstrap:app` and verify it matches expectations.

5. Verify that `webcompy start --dev --app docs_src.bootstrap:app` still works correctly (SSR renders pages, browser hydration works).

6. Run the full test suite: `uv run python -m pytest tests/ --tb=short`.

7. Run lint and typecheck: `uv run ruff check .` and `uv run pyright`.

8. Update `docs_src/webcompy-lock.json` if it has changed (commit the updated lockfile).

### Important Notes

- The root `pyproject.toml` `[dependency-groups] docs` entry should remain unchanged — it's still useful for `uv sync --group docs` at the project root level.
- The new `docs_src/pyproject.toml` is a minimal project file that exists only to provide `[project.optional-dependencies.browser]` for `dependencies_from` resolution.
- Do NOT add `docs_src/pyproject.toml` to `.gitignore` — it should be version-controlled.
- Do NOT create a `docs_src/uv.lock` file — the lock is managed by `webcompy-lock.json`.

### Acceptance Criteria

- `docs_src/pyproject.toml` exists with `[project.optional-dependencies] browser = ["numpy", "matplotlib"]`.
- `docs_src/webcompy_config.py` uses `dependencies=None, dependencies_from="browser"`.
- `docs_src/webcompy_server_config.py` has `lockfile_sync_config = LockfileSyncConfig(sync_group="browser")`.
- `docs_src/webcompy-lock.json` is regenerated and correct.
- `webcompy start --dev --app docs_src.bootstrap:app` works.
- All existing tests pass.
- Lint and typecheck pass.