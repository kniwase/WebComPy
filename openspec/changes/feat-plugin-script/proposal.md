## Why

WebComPy currently loads all JavaScript scripts unconditionally — every `<script>` added via `app.append_script()` is embedded in the generated HTML. There is no mechanism to conditionally load scripts based on runtime conditions (e.g., URL query parameters). This forces developers to either always incur the cost of third-party scripts (like eruda debug toolbar) or manually write raw JavaScript inline.

PyScript provides native mechanisms for JS module loading (`js_modules` in py-config) and lifecycle hooks (`hooks.main.*` / `hooks.worker.*`), but these have different purposes: `js_modules` is for ES modules consumed by Python code, and PyScript hooks are for interpreter-level instrumentation. A lightweight mechanism for conditional, runtime-dependent `<script>` injection is missing.

## What Changes

- **Add `PluginScript` dataclass**: A typed descriptor for a script that may be loaded conditionally. Contains `attrs` (HTML script attributes), optional inline `script`, optional `condition` (JS expression evaluated at runtime), and `in_head` flag.
- **Add `AppConfig.scripts` field**: A `list[PluginScript]` on `AppConfig` that declaratively defines conditional scripts.
- **Extend `generate_html()`**: Convert `PluginScript` instances with a `condition` into wrapper `<script>` tags containing JS that evaluates the condition and dynamically creates the actual `<script>` element. Scripts without a condition are rendered as static `<script>` tags (preserving existing behavior).
- **Support `?debug=True` query parameter pattern**: The `condition` field accepts arbitrary JS expressions. The primary motivating use case is enabling eruda via `new URLSearchParams(location.search).get('debug') === 'True'`.

## Known Issues Addressed

- Partially addresses "No plugin system" — this is the foundational layer that `feat-plugin-system` will later build upon.

## Non-goals

- **No Python-side plugin lifecycle hooks** — `PluginScript` is purely a JS script loading mechanism. Full plugin lifecycle (on_app_init, on_app_ready, etc.) is deferred to `feat-plugin-system`.
- **No plugin discovery/loading** — `AppConfig.plugins` field (for auto-importing plugin classes) is deferred to `feat-plugin-system`.
- **No router guards or navigation middleware** — router-level hooks are in scope for `feat-plugin-system`, not this change.
- **No server-side condition evaluation** — conditions are always evaluated in the browser at runtime, preserving SSG compatibility.

## Capabilities

### New Capabilities
- `plugin-script`: Conditional, declarative JavaScript script loading via `PluginScript` descriptors in `AppConfig`.

### Modified Capabilities
- `app-config`: `AppConfig` gains a `scripts: list[PluginScript]` field. This is additive — no existing fields or behavior are changed.

## Impact

- **Affected code**:
  - `webcompy/app/_config.py`: Add `PluginScript` dataclass, add `scripts` field to `AppConfig`
  - `webcompy/cli/_html.py`: Extend `generate_html()` to handle conditional scripts
  - `webcompy/app/__init__.py`: Export `PluginScript` in public API
- **Consumer change**:
  - `docs_app/bootstrap.py`: Replace two eruda `append_script()` calls with a `PluginScript` in `AppConfig`
- **No new external dependencies**
