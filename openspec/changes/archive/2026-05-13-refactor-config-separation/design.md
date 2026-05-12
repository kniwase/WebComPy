## Context

WebComPy currently uses a single `AppConfig` dataclass that contains both browser-relevant settings (e.g., `base_url`, `profile`, `hydrate`, `plugins`) and server-only build settings (e.g., `app_package`, `dependencies`, `serve_all_deps`, `wasm_serving`, `runtime_serving`, `standalone`, `wheel_mode`, `assets`, `version`). This coupling prevents using WebComPy as a library in a PyScript environment without importing server-only configuration. The project also uses two separate configuration files (`webcompy_config.py` and `webcompy_server_config.py`) and an `app_import_path` string to discover the app instance at CLI time.

The mount selector is passed to `app.run(selector="#my-app")` at runtime only, but SSR/SSG generates HTML with a hardcoded `id="webcompy-app"` div, creating an inconsistency if the runtime selector differs.

## Goals / Non-Goals

**Goals:**
- Separate browser-relevant config from server-only build config into distinct packages (`webcompy.app` vs `webcompy.cli.config`)
- Enable library usage: import WebComPy components in PyScript without server-only config
- Unify the mount selector across browser runtime, SSR, and SSG
- Consolidate two config files into one (`webcompy_config.py`)
- Replace `--app` flag with `--config` flag for explicit config file specification
- Eliminate `app_import_path` — the `WebComPyBuildConfig.app` field replaces it
- Make `WebComPyBuildConfig` the single source of truth for all build-time settings
- Rename `bootstrap.py` to `app.py` for clarity

**Non-Goals:**
- Multi-app support within a single browser page (future concern)
- Plugin system redesign (out of scope)
- Lock file format changes
- PyScript/Pyodide version upgrades

## Decisions

### D1: Three-tier config class hierarchy

```
WebComPyAppConfig (webcompy.app._config)
  ├── base_url, selector, profile, hydrate, scripts, plugins

WebComPyServerConfig (webcompy.cli.config._server_config)
   ├── port, dev
 
WebComPyBuildConfig (webcompy.cli.config._build_config)
  ├── app_module: ModuleType (required, first positional arg - the app's Python module)
  ├── app_var: str = "app" (name of the WebComPyApp instance variable in that module)
  ├── app: WebComPyApp (computed from app_module + app_var in __post_init__)
  ├── app_package_path: Path (computed from app_module.__file__ in __post_init__)
  ├── server: WebComPyServerConfig
  ├── dependencies, dependencies_from, assets, version
  ├── serve_all_deps, wasm_serving, runtime_serving
  ├── standalone, wheel_mode
  ├── dist, cname, static_files_dir
  └── lockfile_sync_config
```

**Rationale**: `WebComPyAppConfig` stays in `webcompy.app` so browser code only imports from `webcompy.app`. `WebComPyBuildConfig` and `WebComPyServerConfig` live in `webcompy.cli.config` — this ensures they are automatically excluded from browser wheels because `_BROWSER_ONLY_EXCLUDE = {"cli"}` already excludes the entire `webcompy/cli/` subtree from browser bundles. `WebComPyServerConfig` is a member of `WebComPyBuildConfig` rather than a peer, because server settings are always used in the context of a build/serve operation.

**Alternative considered**: Keep all configs in `webcompy.app` — rejected because browser code would transitively import server-only types. Another alternative: `webcompy.config` as a top-level package — rejected because it would require adding `"config"` to `_BROWSER_ONLY_EXCLUDE` separately.

### D2: `WebComPyBuildConfig.app_module` + `app_var` pattern

`WebComPyBuildConfig` takes the app's **module object** (`import my_app.app as app_module`) as its first required positional argument, plus `app_var: str = "app"` for the instance variable name. This replaces `app_import_path` entirely.

```python
import my_app.app as app_module
from webcompy.cli.config import WebComPyBuildConfig, WebComPyServerConfig

config = WebComPyBuildConfig(app_module, ...)
```

In `__post_init__`:
```python
self.app_package_path = Path(self.app_module.__file__).parent
self.app = getattr(self.app_module, self.app_var)
```

The `app` attribute is a convenience accessor for `getattr(app_module, app_var)`. The `app_package_path` is derived from the module's `__file__` — since the module is `my_app/app.py`, its parent directory is the app package root (`my_app/`).

**Rationale**: Using the module object instead of the `WebComPyApp` instance gives us a reliable source for `app_package_path` via `__file__`, while still providing access to the app instance via `getattr(app_module, app_var)`. Using `import my_app.app as app_module` (not `from my_app import app as app_module`) is critical because the latter returns the `WebComPyApp` instance if `__init__.py` re-exports it, losing access to `__file__`.

**Alternative considered**: `app: WebComPyApp` as first argument with auto-derivation of `app_package_path` from `app.__class__.__module__` — rejected because `app.__class__.__module__` returns `"webcompy.app._app"` (the framework module where `WebComPyApp` is defined), not the user's app module where the instance was created. Cannot auto-derive the package from the instance alone.

### D4: `selector` in `WebComPyAppConfig`

Move the mount selector from `app.run(selector=...)` to `WebComPyAppConfig.selector` with default `"#webcompy-app"`. `WebComPyApp.run()` takes no arguments.

**Rationale**: SSR/SSG generates the mount div using the selector. If it's only in `run()`, the server can't know it, leading to inconsistency. Putting it in config ensures all three environments (browser, SSR, SSG) use the same value.

**Alternative considered**: Keep `run(selector=...)` as an override — rejected because it creates a divergence point between SSR/SSG HTML and runtime behavior.

### D5: Circular import avoidance

`WebComPyBuildConfig` needs only `types.ModuleType` for the `app_module` field — no import from `webcompy.app` is needed at all. The `app` property (WebComPyApp instance) is accessed dynamically via `getattr(app_module, app_var)` in `__post_init__`, so no class reference is required.

```
Dependency graph (no cycles):
  webcompy/app/_config.py                → no internal deps
  webcompy/app/_app.py                   → webcompy/app/_config.py
  webcompy/cli/config/_server_config.py  → no internal deps
  webcompy/cli/config/_build_config.py   → webcompy/cli/config/_server_config.py
                                           → no import from webcompy/app/ at all
```

### D6: Single `webcompy_config.py` file

Consolidate `webcompy_config.py` and `webcompy_server_config.py` into one file:

```python
# webcompy_config.py (server-only)
import my_app.app as app_module
from webcompy.cli.config import WebComPyBuildConfig, WebComPyServerConfig

config = WebComPyBuildConfig(
    app_module,
    dependencies=None,
    dependencies_from="browser",
    standalone=True,
    server=WebComPyServerConfig(port=8080),
)
```

**Rationale**: `webcompy_server_config.py` existed because `ServerConfig` and `GenerateConfig` were separate from `AppConfig`. With `WebComPyBuildConfig` absorbing all build settings, a second file is unnecessary.

### D7: CLI discovery via `--config` flag

Replace `--app my_app.bootstrap:app` with `--config path/to/webcompy_config.py`. When `--config` is not provided, CLI looks for `webcompy_config.py` in CWD by trying `importlib.import_module("webcompy_config")` (CWD is typically on `sys.path`).

The CLI imports the config module and reads `config` (a `WebComPyBuildConfig` instance). From it:
- `config.app` → `WebComPyApp` instance (computed from `app_module` + `app_var`)
- `config.app_package_path` → package directory (from `app_module.__file__` parent)
- `config.server` → `WebComPyServerConfig` instance

`--config` flag value: a Python import path string (e.g., `"path.to.my_config"`), not a filesystem path. The config module's parent directory must be on `sys.path`. The default CWD-based discovery works because CWD is on `sys.path`.

**Rationale**: The `--app` flag required knowing the import path format (`module:attribute`). `--config` is simpler — just point to the config module.

### D8: `bootstrap.py` → `app.py`

Rename the app entry point from `bootstrap.py` to `app.py`. This aligns with the naming convention where `from my_app.app import app` is more intuitive than `from my_app.bootstrap import app`.

## Risks / Trade-offs

- **[Breaking change]** All existing projects must update their config structure, file names, and CLI invocations → No migration path provided; this is a major version break
- **[app_var miss]** If the `WebComPyApp` instance variable in `app.py` is named something other than `"app"`, `getattr(app_module, "app")` will raise `AttributeError` → `app_var` parameter allows specifying a different name; this is validated in `__post_init__`
- **[app_module not a module]** If config incorrectly passes a `WebComPyApp` instance directly instead of the module object, `__file__` access will fail → Type check and `hasattr(self.app_module, '__file__')` validation in `__post_init__`
- **[webcompy_config.py imports app]** Importing `app_module` in `webcompy_config.py` means the app module is loaded during config discovery. If the app module has side effects or heavy imports, this could slow down CLI startup → Acceptable trade-off; the app is needed anyway for SSR/SSG
- **[BuildConfig dataclass size]** `WebComPyBuildConfig` has many fields (absorbing `GenerateConfig` fields) → Acceptable because it's server-only code in `webcompy/cli/config/`, automatically excluded from browser wheels
- **[--config import path ambiguity]** `--config` expects a Python import path (e.g., `"my_project.webcompy_config"`), not a filesystem path. If the config file is not on `sys.path`, discovery fails → Document clearly; CWD is always on `sys.path` for the default case