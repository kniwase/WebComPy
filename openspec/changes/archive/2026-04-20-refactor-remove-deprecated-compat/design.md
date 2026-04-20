## Context

WebComPy currently has two configuration paths:

1. **Legacy**: `webcompy_config.py` containing a `WebComPyConfig` instance → `get_config()` discovers it → `get_app(config)` finds the app → CLI functions use `WebComPyConfig` fields throughout
2. **New**: `WebComPyApp(config=AppConfig(...))` → `--app` flag imports the app directly → `build_config_from_app()` converts `AppConfig` back to `WebComPyConfig` internally

The internal `AppConfig` → `WebComPyConfig` conversion (`build_config_from_app`) means the CLI code still reads from `WebComPyConfig` fields everywhere (`config.base`, `config.app_package_path`, `config.dependencies`, etc.). There's also an `app.__component__` deprecated property with a `DeprecationWarning`.

Additionally, `ServerConfig` and `GenerateConfig` are exported publicly but are only used internally by CLI functions — they're not meant for developers to pass to `WebComPyApp`.

Current file dependency map:
```
WebComPyConfig (central dependency, to be removed)
    ├── cli/_config.py          — class definition
    ├── cli/_utils.py            — get_config(), get_app(), build_config_from_app()
    ├── cli/_server.py           — create_asgi_app(config), run_server()
    ├── cli/_generate.py         — generate_static_site()
    ├── cli/_html.py             — generate_html(config)
    ├── cli/_asgi_app.py         — module-level ASGI app (legacy)
    ├── cli/__init__.py          — public export
    ├── cli/template_data/       — project template
    ├── tests/e2e/               — e2e config
    ├── tests/test_config.py     — WebComPyConfig tests
    └── tests/test_app_instance.py — deprecation tests
```

## Goals / Non-Goals

**Goals:**
- Remove `WebComPyConfig`, `app.__component__`, and all `DeprecationWarning` bridges
- Establish a clean two-file configuration pattern (`webcompy_config.py` + `webcompy_server_config.py`)
- Make `AppConfig` the sole developer-facing configuration class
- Make `ServerConfig` and `GenerateConfig` internal-only (not in public `__all__`)
- Refactor CLI internals to use typed config dataclasses directly instead of converting through a legacy class
- Keep `--dev`, `--port`, `--dist` CLI flags as overrides for config file values
- Keep `--app` flag for direct import path specification

**Non-Goals:**
- Adding new features or configuration options
- Changing browser runtime behavior
- Modifying DI, reactive, component, or element systems
- Removing CLI commands (`start`, `generate`, `init`)
- Changing the PyScript bootstrapping mechanism

## Decisions

### Decision 1: Two-file configuration pattern

**Choice**: `webcompy_config.py` (app-shared settings) + `webcompy_server_config.py` (server-only settings)

**Rationale**: Separating browser-relevant config from server-relevant config follows Angular's pattern of `angular.json` vs server config. The app's `bootstrap.py` imports `app_config` from `webcompy_config.py` for use in the browser, while `ServerConfig`/`GenerateConfig` are only needed by CLI functions on the server side. This prevents browser code from importing server-only dependencies.

**Alternatives considered**:
- Single `webcompy_config.py` containing everything: mixes browser/server concerns, `bootstrap.py` in browser would import `ServerConfig`
- No config files, all in `bootstrap.py`: no way for CLI to discover settings without `--app` flag; also browser `bootstrap.py` would need to contain server settings
- `--app` mandatory only: too strict for simple projects, developers must know import paths

### Decision 2: `app_import_path` in `webcompy_config.py`

**Choice**: `webcompy_config.py` contains `app_import_path = "my_app.bootstrap:app"` so the CLI can discover the app without `--app`.

**Rationale**: Provides a zero-argument `python -m webcompy start` experience. The CLI checks `--app` first, then falls back to `webcompy_config.py`. The `app_import_path` string is a standard Python import path format (`module.path:variable_name`).

### Decision 3: CLI flag overrides for config values

**Choice**: `--dev`, `--port`, `--dist` CLI flags override `ServerConfig`/`GenerateConfig` values from `webcompy_server_config.py`.

**Rationale**: Developers frequently want to override config values from the command line (e.g., `--dev` for hot-reload, `--port 3000`). These overrides are applied after loading config file values.

### Decision 4: `generate_html()` takes `WebComPyApp` instead of config

**Choice**: `generate_html(app, dev_mode, prerender, app_version, app_package_name)` — takes the `WebComPyApp` instance and reads `app.config` internally.

**Rationale**: `generate_html` previously consumed `WebComPyConfig` fields (`config.base`, `config.dependencies`, `config.app_package_path`). These all exist on `app.config` (`AppConfig`). Passing the app instance is simpler and eliminates the need for a config parameter entirely.

### Decision 5: `create_asgi_app` takes typed config dataclasses

**Choice**: `create_asgi_app(app, server_config=None)` where `server_config` is `ServerConfig | None`.

**Rationale**: Eliminates `WebComPyConfig` from the function signature. `AppConfig` is accessed from `app.config`. `ServerConfig` is a clean, typed dataclass for server-specific settings. When `None`, defaults are used. `dev_mode` parameter is replaced by `ServerConfig.dev`.

### Decision 6: `generate_static_site` takes typed config dataclasses

**Choice**: `generate_static_site(app, generate_config=None)` where `generate_config` is `GenerateConfig | None`.

**Rationale**: Same rationale as Decision 5. Eliminates `WebComPyConfig`. `AppConfig` from `app.config`. `GenerateConfig` for SSG-specific settings.

### Decision 7: `ServerConfig` and `GenerateConfig` become internal

**Choice**: Remove from `webcompy/__init__.py` and `webcompy/app/__init__.py` `__all__`. Developers access them via `webcompy.app._config` if needed, but the primary interface is through `webcompy_server_config.py`.

**Rationale**: These are configuration containers for CLI-internal use. Developers shouldn't need to import them directly in normal workflows — they define them in `webcompy_server_config.py`.

### Decision 8: Remove `_asgi_app.py`

**Choice**: Delete `webcompy/cli/_asgi_app.py` entirely.

**Rationale**: It was a module-level ASGI app that relied on `get_config()` (legacy pattern). Developers who need a module-level ASGI app for uvicorn can write their own 3-line file. No need for the framework to maintain this.

### Decision 9: Remove `app.__component__`

**Choice**: Delete the `__component__` property entirely from `WebComPyApp`.

**Rationale**: All forwarded properties (`routes`, `router_mode`, `set_path`, `head`, `style`, `scripts`, `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`) are already available on the app instance. The deprecated property serves no purpose.

## Risks / Trade-offs

- **[Breaking change]** All `WebComPyConfig` users must migrate to `AppConfig` + two-file pattern → Mitigation: this is a pre-release, breaking changes are acceptable. Migration guide: replace `WebComPyConfig(app_package=..., base=..., ...)` with `AppConfig(app_package=..., base_url=..., ...)` in `webcompy_config.py`, move server settings to `webcompy_server_config.py`.
- **[Breaking change]** `_asgi_app.py` removal means `uvicorn webcompy.cli._asgi_app:asgi_app` no longer works → Mitigation: documented migration is to write a 3-line script file.
- **[Breaking change]** `app.__component__` removal → Mitigation: all forwarded properties exist; no known usage of `__component__` outside the framework itself.
- **[Risk]** `webcompy_config.py` is imported both by CLI (server) and `bootstrap.py` (browser) → Mitigation: only `AppConfig` is in `webcompy_config.py`, which has no server-only imports. `ServerConfig`/`GenerateConfig` are in a separate file.
- **[Risk]** `app_import_path` string could become stale → Mitigation: standard Python convention, validated at runtime with clear error messages from `get_app_from_import_path()`.