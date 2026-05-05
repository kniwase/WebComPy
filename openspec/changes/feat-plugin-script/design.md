## Context

WebComPy's `generate_html()` currently renders all `<script>` elements unconditionally — every call to `app.append_script()` results in a `<script>` tag in the output HTML. There is no way to defer script loading until a runtime condition is met. The PyScript layer itself provides `js_modules` (for ES modules consumed by Python) and plugin hooks (for interpreter instrumentation), neither of which address the need for conditionally injecting arbitrary `<script>` tags.

The `AppConfig` dataclass currently holds 12 fields (app_package, base_url, dependencies, etc.) but has no mechanism for declaring scripts with runtime conditions.

## Goals / Non-Goals

**Goals:**
- Provide a `PluginScript` dataclass that declaratively describes a script (attributes, inline code, optional runtime condition, head/body placement)
- Add `AppConfig.scripts: list[PluginScript]` as a zero-config field (empty by default)
- Extend `generate_html()` to render conditional scripts as wrapper `<script>` tags with inline JS condition evaluation
- Preserve existing behavior for scripts without a condition (static `<script>` tags unchanged)
- Enable the `?debug=True` pattern for eruda without raw JS in bootstrap

**Non-Goals:**
- No Python lifecycle hooks, plugin discovery, or plugin classes — deferred to `feat-plugin-system`
- No modification to `append_script()` API — it remains the imperative counterpart
- No server-side condition evaluation — all conditions evaluate in the browser
- No bundling or CSP optimizations for the wrapper script

## Decisions

### Decision 1: Place PluginScript in `webcompy/app/_config.py`

`PluginScript` is a configuration descriptor, not a runtime object. Co-locating it with `AppConfig` keeps the public API surface minimal — users import both from `webcompy.app`.

Alternatives considered:
- `webcompy/plugin/` — premature; `plugin` package creation is deferred to `feat-plugin-system`
- `webcompy/elements/` — scripts are rendered as elements but PluginScript is a config concept, not a DOM element

### Decision 2: Flat PluginScript dataclass (not nested under conditions)

```python
@dataclass
class PluginScript:
    attrs: dict[str, str]          # HTML <script> attributes (src, type, etc.)
    script: str | None = None      # inline JS code
    condition: str | None = None   # JS expression evaluated at runtime (e.g., "location.search.includes('debug')")
    in_head: bool = False          # place in <head> (True) or at end of <body> (False)
```

A single condition per-script is sufficient for the initial use case. Grouping scripts by condition can be done later if needed.

Alternatives considered:
- `condition: Callable[[], bool]` — Python callables can't be serialized to HTML for SSG
- Dict-based API — less type-safe than a dataclass

### Decision 3: Render conditional scripts as self-contained wrapper `<script>` tags

Each `PluginScript` with a `condition` produces a wrapper `<script>` with inline JS. Two variants:

**Case A: External script (`src` in attrs):**
```html
<script>
(function(){
  if (<condition>) {
    var __wc_s = document.createElement('script');
    __wc_s.type = '<type>';
    __wc_s.src = '<src>';
    __wc_s.onload = function() { <inline script>; };
    (in_head ? document.head : document.body).appendChild(__wc_s);
  }
})();
</script>
```

**Case B: Inline-only script (`script` but no `src`):**
```html
<script>
(function(){
  if (<condition>) {
    <inline script>
  }
})();
</script>
```

When a PluginScript has `script` but no `src`, the inline code executes directly inside the `if` block. No `onload` is needed since there is no external resource to load.

The wrapper `<script>` tag's DOM placement follows `in_head`: `in_head=True` places the wrapper in `<head>`, `in_head=False` places it at the end of `<body>`.

This approach:
- Works identically in dev server and SSG (no server-side logic needed)
- Is self-contained (no external dependencies)
- Handles script ordering via `onload` callbacks when external scripts are needed

Alternatives considered:
- PyScript `js_modules` — requires ES module format; not all scripts (like eruda) are ES modules
- PyScript hooks (`hooks.main.onReady`) — requires separate JS file loaded before core.js; adds complexity for simple conditional scripts
- `document.write()` — blocked by CSP in many environments

### Decision 4: One wrapper per PluginScript

Each conditional PluginScript generates its own wrapper. This keeps the implementation simple and avoids the complexity of deduplicating conditions.

Multiple scripts with the same condition will produce multiple wrappers. This is an acceptable overhead for the initial version.

## Risks / Trade-offs

- **[Low] Multiple wrappers for same condition** → Each PluginScript with an identical condition produces its own wrapper `<script>`. Mitigation: Acceptable for eruda (2 scripts). Can optimize later by grouping.
    - **[Low] No validation on attrs** → The `attrs: dict[str, str]` field accepts arbitrary key-value pairs without validation. Invalid HTML attributes or unsafe values are passed through to the generated HTML. Mitigation: Document that attrs is passed through verbatim. Future versions may add validation for known-safe attribute names.
- **[Low] CSP restrictions** → Inline wrapper scripts use `onload` callbacks. Mitigation: Document CSP implications. Future versions may support nonce-based approaches.
- **[None] No breaking changes** — existing `append_script()` and static scripts are unchanged.

## Open Questions

None. The design is sufficiently constrained and the implementation surface is small.
