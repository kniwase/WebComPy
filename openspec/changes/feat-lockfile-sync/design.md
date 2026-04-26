# Design: Lock File Sync — Bidirectional Version Synchronization

## Design Decisions

### D1: Export generates `requirements.txt` with pinned versions

The simplest and most universal format for pinned dependencies is `requirements.txt` with `package==version` lines. This format is consumable by `pip install -r`, `uv pip install -r`, and many CI systems.

Packages that require local installation are included:
- `bundled_packages` (all entries) — must be installed locally for SSR/SSG
- `pyodide_packages` with `is_wasm=False` (non-WASM Pyodide CDN packages) — required locally for SSR/SSG rendering, even though the browser loads them from the Pyodide CDN

WASM-only `pyodide_packages` are excluded because they are not needed in the local environment — they are loaded from the Pyodide CDN at browser runtime and are typically C extensions compiled for WASM. WebComPy is an SSR/SSG-only framework, so all non-WASM packages must be locally available for server-side rendering.

### D2: Sync reads `requirements.txt` and `pyproject.toml` via auto-discovery

Two sync sources are supported, discovered automatically via project root detection:

1. **`requirements.txt`**: Parse lines matching `package==version` or `package>=version` patterns. Only `==` pinned versions are used for comparison; other specifiers are reported as informational.

2. **`pyproject.toml`**: Read dependency entries based on `LockfileSyncConfig.sync_group`:
   - When `sync_group` is `None`: read `[project.dependencies]` (PEP 621 format)
   - When `sync_group` is set (e.g., `"browser"`): read `[project.optional-dependencies.browser]`

   Only `==` pinned versions contribute to comparison; version ranges are reported as informational with suggestions to pin.

Other formats (`Pipfile`, `poetry.lock`, `uv.lock`) are out of scope. `poetry.lock` and `uv.lock` are lock files in their own right — synchronizing between them and `webcompy-lock.json` introduces complex version resolution that is better handled by running `webcompy lock` after `poetry install` or `uv sync`.

### D3: Sync is compare-and-report, not auto-modify

`--sync` compares the detected versions with the lock file entries and:
- Reports matching versions (informational)
- Reports mismatches (warnings with suggested fixes)
- Reports packages in external config but not in lock file (informational — may be non-browser dependencies)
- Reports packages in lock file but not in external config (informational — transitive deps)

It does NOT modify the lock file. The correct workflow is:
1. Run `webcompy lock --sync` to see what differs
2. Install or update packages as needed
3. Run `webcompy lock` to regenerate the lock file

This avoids the complexity of partial lock file updates and keeps the lock file as the single source of truth for WebComPy builds.

### D4: `--install` uses uv-first pip invocation

`webcompy lock --install` combines export + install:
1. Generate `requirements.txt` using `export_requirements()`
2. Install packages using the first available tool:
   - `uv pip install -r {path}` if `uv` is available (checked via `shutil.which("uv")`)
   - `sys.executable -m pip install -r {path}` as fallback
3. Propagate the install command's exit code

This prioritizes `uv` because WebComPy itself uses `uv` for package management, and `uv pip` is significantly faster than `pip`. The fallback to `sys.executable -m pip` ensures compatibility in environments where only `pip` is available.

### D5: Project root auto-discovery replaces explicit `--path`

All lock file sync commands use auto-discovery to locate `requirements.txt` and `pyproject.toml`. The `--path` flag is eliminated in favor of:

1. **Explicit configuration**: `LockfileSyncConfig.requirements_path` in `webcompy_server_config.py` (optional, app_package-relative path)
2. **Auto-discovery**: When no explicit path is configured, walk up from `app_package_path` until a directory containing `pyproject.toml` is found — that directory is the project root. The search stops at `pyproject.toml` (which marks the project boundary) and does not traverse beyond it.
3. **Error on failure**: If `pyproject.toml` is not found anywhere above `app_package_path`, report an error instructing the developer to set `LockfileSyncConfig.requirements_path` explicitly.

When a path is discovered for the first time, it is written to `LockfileSyncConfig.requirements_path` in `webcompy_server_config.py` so subsequent invocations skip the discovery step.

### D6: `LockfileSyncConfig` in `webcompy_server_config.py`

A new dataclass `LockfileSyncConfig` stores lock file sync settings alongside `ServerConfig` and `GenerateConfig`:

```python
@dataclass
class LockfileSyncConfig:
    requirements_path: str | None = None    # app_package-relative path or None (auto-discover)
    sync_group: str | None = None           # pyproject.toml [project.optional-dependencies] key
```

This follows the existing pattern where `webcompy_server_config.py` contains server/CLI-only settings that are not needed in the browser environment.

### D7: `sync_group` for multi-environment pyproject.toml projects

When a `pyproject.toml` contains multiple optional dependency groups (e.g., `dev`, `browser`, `docs`), `sync_group` specifies which group represents the WebComPy browser dependencies:

```toml
[project.optional-dependencies]
dev = ["pytest", "ruff"]
browser = ["numpy", "matplotlib"]
```

With `lockfile_sync_config = LockfileSyncConfig(sync_group="browser")`, `--sync` compares only `[project.optional-dependencies.browser]` against the lock file, avoiding noise from dev-only or docs-only dependencies.

When `sync_group` is `None`, `[project.dependencies]` is used (the default, suitable for projects where all dependencies are browser-relevant).

## Architecture

### Command Flow

```
webcompy lock
├── (no flags)       → generate/update lock file (existing behavior)
├── --export         → generate requirements.txt from lock file via auto-discovery
├── --sync           → compare external config with lock file via auto-discovery
├── --install        → export + uv/pip install
└── (flags are mutually exclusive)
```

### Auto-Discovery Algorithm

```
START: app_package_path (where webcompy-lock.json lives)

Step 1: Check LockfileSyncConfig.requirements_path
  → If set: use it (resolve relative to app_package_path), DONE

Step 2: Walk up from app_package_path looking for pyproject.toml
  for dir in app_package_path.parents:
      if (dir / "pyproject.toml").exists():
          project_root = dir
          break
  else:
      → ERROR: "pyproject.toml not found above app package.
         Set LockfileSyncConfig.requirements_path in webcompy_server_config.py."

Step 3: Locate sync sources in project_root
  requirements_txt = project_root / "requirements.txt"  (may not exist yet)
  pyproject_toml   = project_root / "pyproject.toml"   (exists by definition)

Step 4: Record discovered path
  → Write LockfileSyncConfig.requirements_path to webcompy_server_config.py
    (relative path from app_package_path to project_root / "requirements.txt")
```

### Export Logic

```
webcompy-lock.json
    │
    ├── bundled_packages:
    │     markupsafe → version="2.1.5"  ──→  markupsafe==2.1.5
    │     click → version="8.1.7"       ──→  click==8.1.7
    │
    ├── pyodide_packages:
    │     numpy → is_wasm=True           ──→  (excluded)
    │     jinja2 → is_wasm=False         ──→  jinja2==3.1.6
    │
    └── result: requirements.txt
         markupsafe==2.1.5
         click==8.1.7
         jinja2==3.1.6
```

### Sync Logic

```
Auto-discovered sources:
  requirements.txt (if exists)
  pyproject.toml   (always exists after discovery)

requirements.txt comparison:
    charset-normalizer==3.4.0
    requests==2.32.4
    numpy==2.2.5           ← WASM, not in local install set
    some-tool==1.0.0       ← not in lock file
    │
    └── Report:
         ✓ charset-normalizer: 3.4.0 (matches)
         ⚠ requests: lock=2.32.4, requirements.txt=2.31.0 (mismatch)
         ℹ numpy: WASM package, not applicable for local install
         ℹ some-tool: not in lock file (non-browser dependency?)

pyproject.toml comparison (sync_group=None):
    [project]
    dependencies = [
        "markupsafe==2.1.5",
        "requests>=2.31",
    ]
    │
    └── Report:
         ✓ markupsafe: 2.1.5 (matches)
         ℹ requests: not pinned (">=2.31"), lock file has 2.32.4
           Suggest: pin to requests==2.32.4

pyproject.toml comparison (sync_group="browser"):
    [project.optional-dependencies]
    browser = [
        "numpy",
        "matplotlib",
    ]
    │
    └── Report:
         ℹ numpy: not pinned (bare name), lock file has 2.2.5 (WASM, N/A for local install)
         ℹ matplotlib: not pinned (bare name), lock file has 3.8.4 (WASM, N/A for local install)
```

### Install Logic

```
webcompy lock --install
    │
    ├── 1. Auto-discover requirements_path (same as --export)
    ├── 2. Export lockfile → requirements.txt
    ├── 3. Install:
    │     if shutil.which("uv"):
    │         subprocess.run(["uv", "pip", "install", "-r", path])
    │     else:
    │         subprocess.run([sys.executable, "-m", "pip", "install", "-r", path])
    └── 4. Propagate exit code
```

## Implementation

### `_lockfile_sync.py` (New Module)

```python
def discover_project_root(app_package_path: pathlib.Path) -> pathlib.Path: ...
def discover_requirements_path(
    app_package_path: pathlib.Path,
    lockfile_sync_config: LockfileSyncConfig | None,
) -> pathlib.Path: ...
def export_requirements(
    lockfile: Lockfile,
    path: pathlib.Path,
) -> None: ...
def sync_from_requirements_txt(
    lockfile: Lockfile,
    path: pathlib.Path,
) -> list[str]: ...
def sync_from_pyproject_toml(
    lockfile: Lockfile,
    path: pathlib.Path,
    sync_group: str | None,
) -> list[str]: ...
def install_requirements(
    lockfile: Lockfile,
    path: pathlib.Path,
) -> None: ...
```

### `_lock.py` Extensions

```python
def lock_command() -> None:
    # Existing: no flags → generate/update lock file
    # New:
    # --export  → export_requirements() via auto-discovery
    # --sync    → sync_from_*() via auto-discovery
    # --install → install_requirements() via auto-discovery
```

### `webcompy/app/_config.py` Extensions

```python
@dataclass
class AppConfig:
    # ... existing fields ...
    dependencies: list[str] | None = None       # None = auto-populate from pyproject.toml
    dependencies_from: str | None = None       # pyproject.toml group key (None = [project.dependencies])

@dataclass
class LockfileSyncConfig:
    requirements_path: str | None = None
    sync_group: str | None = None
```

## Specs to Update

- `openspec/specs/lockfile/spec.md` — add export/sync/install requirements
- `openspec/specs/cli/spec.md` — add CLI flags for `webcompy lock`
- `openspec/specs/project-config/spec.md` — add LockfileSyncConfig and project setup examples

### D8: `AppConfig.dependencies` defaults to `None`, auto-populated from `pyproject.toml`

`AppConfig.dependencies` changes from `list[str]` (default `[]`) to `list[str] | None` (default `None`). When `None`, the CLI resolves dependencies from `pyproject.toml` using the same `sync_group` key as `LockfileSyncConfig`:

```
AppConfig(dependencies=None, dependencies_from="browser")
                    ↓
discover_project_root(app_package_path)
    → find pyproject.toml
    → read [project.optional-dependencies.browser]
    → ["numpy", "matplotlib"]
                    ↓
app.config.dependencies = ["numpy", "matplotlib"]  (populated)
```

When `dependencies` is explicitly set (e.g., `dependencies=["numpy", "matplotlib"]`), it takes precedence and no auto-discovery occurs. This preserves backward compatibility — existing `webcompy_config.py` files with explicit `dependencies` lists continue to work unchanged.

The `dependencies_from` field in `AppConfig` specifies the `sync_group` key to read from `pyproject.toml`:
- `dependencies_from=None` (default): read `[project.dependencies]`
- `dependencies_from="browser"`: read `[project.optional-dependencies.browser]`

This eliminates the manual duplication where developers currently write the same dependency list in both `AppConfig.dependencies` and `pyproject.toml`.

The resolution happens in `discover_app()` (or a new function called from it), which already has access to `app_package_path` for project root discovery.

### D9: `dependencies_from` and `sync_group` should match

When both `AppConfig.dependencies_from` and `LockfileSyncConfig.sync_group` are set, they SHOULD match. If they differ, a warning is emitted:

```
⚠ AppConfig.dependencies_from="browser" differs from LockfileSyncConfig.sync_group="deps"
  This may cause inconsistencies between lock file generation and sync comparison.
```

When `dependencies_from` is set and `sync_group` is not (defaults to `None`), or vice versa, no warning is emitted — the developer may intentionally use different groups for different purposes.

## Architecture (updated)

### `webcompy/app/_config.py` Extensions

```python
@dataclass
class AppConfig:
    app_package: Path | str = "."
    base_url: str = "/"
    dependencies: list[str] | None = None       # None = auto-populate from pyproject.toml
    dependencies_from: str | None = None       # pyproject.toml group key (None = [project.dependencies])
    assets: dict[str, str] | None = None
    version: str | None = None
    profile: bool = False
    hydrate: bool = True
```

### Dependency Resolution Flow

```
discover_app() or resolve_dependencies()
    │
    ├── app.config.dependencies is not None?
    │   → Use as-is (backward compatible)
    │
    ├── app.config.dependencies is None?
    │   ├── dependencies_from is None?
    │   │   → Read [project.dependencies] from pyproject.toml
    │   ├── dependencies_from is "browser"?
    │   │   → Read [project.optional-dependencies.browser] from pyproject.toml
    │   └── Result → app.config.dependencies = [...]
    │
    └── pyproject.toml not found and dependencies is None?
        → Error: "Could not resolve dependencies from pyproject.toml.
           Either set AppConfig.dependencies explicitly or ensure pyproject.toml exists."
```

## Specs to Update

- `openspec/specs/app-config/spec.md` — add `dependencies` default change and `dependencies_from` requirement
- `openspec/specs/lockfile/spec.md` — add export/sync/install requirements
- `openspec/specs/cli/spec.md` — add CLI flags for `webcompy lock` and dependency resolution
- `openspec/specs/project-config/spec.md` — add LockfileSyncConfig and project setup examples

## Non-goals (restated)

- Automatic package downloading from PyPI
- Synchronizing with `poetry.lock` or `uv.lock`
- Modifying `requirements.txt` or `pyproject.toml` in place
- Removing dependency on local package installation
- Project root discovery beyond pyproject.toml (no `.git`-based or marker-file heuristics)
- AST-based import scanning (unreliable for dynamic imports, conditional imports, etc.)