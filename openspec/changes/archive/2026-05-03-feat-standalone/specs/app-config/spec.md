# App Configuration — Delta: feat-standalone

## ADDED Requirements

### Requirement: AppConfig shall include a standalone flag for complete offline capability
`AppConfig` SHALL include a `standalone: bool = False` field. When `True`, all local-serving modes are enabled simultaneously: `serve_all_deps` SHALL be forced to `True`, `wasm_serving` SHALL default to `"local"`, and `runtime_serving` SHALL default to `"local"`. Individual config options explicitly set by the developer SHALL take precedence over `standalone` defaults.

#### Scenario: Enabling standalone mode with defaults
- **WHEN** a developer creates `AppConfig(standalone=True)` without overriding individual settings
- **THEN** `serve_all_deps` SHALL be `True`
- **AND** `wasm_serving` SHALL be `"local"`
- **AND** `runtime_serving` SHALL be `"local"`
- **AND** the build SHALL produce a fully self-contained output with zero external CDN requests
- **AND** `py-config` SHALL include `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"` (via `runtime_serving="local"`)
- **AND** `py-config` SHALL include `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"` (via `runtime_serving="local"`)

#### Scenario: Individual overrides take precedence
- **WHEN** a developer creates `AppConfig(standalone=True, wasm_serving="cdn")`
- **THEN** the explicit `wasm_serving="cdn"` SHALL take precedence over the `standalone` default
- **AND** WASM packages SHALL be loaded from the CDN
- **AND** `runtime_serving` SHALL still default to `"local"` and `serve_all_deps` SHALL be `True`

#### Scenario: standalone=True forces serve_all_deps=True
- **WHEN** a developer creates `AppConfig(standalone=True, serve_all_deps=False)`
- **THEN** `serve_all_deps` SHALL be `True` (standalone overrides)
- **AND** a warning SHALL be emitted that `standalone=True` forces `serve_all_deps=True`

#### Scenario: standalone=False does not affect other settings
- **WHEN** a developer creates `AppConfig(standalone=False)`
- **THEN** `wasm_serving` SHALL be `"cdn"`, `runtime_serving` SHALL be `"cdn"`, and `serve_all_deps` SHALL be `True` (their own defaults)

### Requirement: Switching standalone mode shall take effect on a fresh configuration
`resolve_standalone_config()` mutates `AppConfig` in place, replacing `None` sentinel values with resolved strings (`"cdn"` or `"local"`). Because `None` sentinels are consumed on the first call, standalone mode switching only takes effect when applied to a fresh `AppConfig` instance (e.g., a new CLI invocation creates a new config). Explicitly set values (`"cdn"` or `"local"`) SHALL be preserved across calls; only `None` sentinel values SHALL be overridden.

#### Scenario: Switching from non-standalone to standalone in a new execution context
- **WHEN** a developer runs `webcompy generate` (non-standalone) and then runs `webcompy generate --standalone`
- **THEN** a fresh `AppConfig` SHALL be created with `standalone=True`
- **AND** `resolve_standalone_config()` SHALL set `wasm_serving` to `"local"`, `runtime_serving` to `"local"`, and `serve_all_deps` to `True`

#### Scenario: Switching from standalone to non-standalone in a new execution context
- **WHEN** a developer runs `webcompy generate --standalone` and then runs `webcompy generate --no-standalone`
- **THEN** a fresh `AppConfig` SHALL be created with `standalone=False`
- **AND** `resolve_standalone_config()` SHALL set `wasm_serving` to `"cdn"`, `runtime_serving` to `"cdn"`, and `serve_all_deps` to `True`

#### Scenario: Explicit values are preserved within a single resolution
- **WHEN** a developer creates `AppConfig(standalone=True, wasm_serving="cdn")`
- **THEN** `resolve_standalone_config()` SHALL preserve `wasm_serving="cdn"` and set `runtime_serving="local"`

#### Scenario: Re-running resolve_standalone_config is idempotent
- **WHEN** `resolve_standalone_config()` is called multiple times on the same `AppConfig` instance
- **THEN** the result SHALL be the same as calling it once
- **AND** no additional warnings SHALL be emitted beyond the first call
