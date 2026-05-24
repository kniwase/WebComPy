## Context

WebComPy currently uses a single monolithic `<style id="webcompy-scoped-styles">` element for all scoped component CSS. This is injected once at initial render (`AppDocumentRoot._render()` guarded by `self.__loading`) and never updated. Lazy-loaded components resolved during SPA navigation add their generators to `ComponentStore` but their CSS is never injected into the DOM. Similarly, SSG generates per-route HTML where each page only includes CSS for components rendered on that specific route, because each route rendering uses the same `ComponentStore` but only renders components for that route.

Head element management (title, meta, links, scripts) is currently imperative through `AppDocumentRoot` methods. The SSG code (`_html.py`) reads these properties and constructs HTML fragments, while browser runtime manipulates the DOM directly. This creates a conceptual split between the two environments.

## Goals / Non-Goals

**Goals:**
- Per-component `<style data-webcompy-cid="...">` injection with idempotent incremental reconciliation
- SSG generates complete scoped CSS in every page (pre-resolve all lazy routes)
- Browser runtime injects missing component styles dynamically on render
- Head element management via VDOM (`HeadElement`), unifying SSG and browser rendering paths
- Backward compatible: consumer code using `app.set_head()` / `app.set_title()` continues to work

**Non-Goals:**
- CSS ordering guarantees beyond cid-based sorting
- Lazy-loading optimization (on-demand CSS injection, code splitting) — all CSS is injected eagerly
- Reactive per-element `<style>` management (removing styles when a component is unregistered) — CSS is append-only
- Head element diffing at individual meta/link granularity — full head reconciliation is sufficient
- Server-side head manipulation during SSR (SSG already reads head state, dev server doesn't manipulate head)

## Decisions

### Decision 1: Per-component `<style>` with `data-webcompy-cid` attribute

Each component's scoped CSS gets its own `<style>` element identified by `data-webcompy-cid="{hash}"`.

```html
<style id="webcompy-scoped-styles">*[hidden]{display:none}</style>
<style data-webcompy-cid="abc">nav[webcompy-cid-abc]{...}</style>
<style data-webcompy-cid="def">.container[webcompy-cid-def]{...}</style>
```

**Alternatives considered:**
- **Single concatenated `<style>`**: Original approach. Cannot incrementally update without full text replacement.
- **CSSStyleSheet API (`adoptedStyleSheets`)**: Would require reconstructing the full sheet on each change — no incremental advantage, and doesn't work with SSG.
- **`<style>` with per-component `id`**: `id` must be document-unique; `data-*` attribute allows multiple style elements per component (future-proof).

**Rationale:** `querySelector('style[data-webcompy-cid="abc"]')` is standard DOM API, idempotent, and SSG-safe. The cid mapping is deterministic from the component name hash.

### Decision 2: Reconcile on render (not on component registration)

`_reconcile_scoped_styles()` is called from `AppDocumentRoot._render()` every render cycle. It scans `ComponentStore.components`, checks which CIDs are missing from the DOM, and injects only missing `<style>` elements.

```python
def _reconcile_scoped_styles(self):
    if ENVIRONMENT != "pyscript":
        return
    dom = inject(DOM_PORT_KEY)
    head = dom.query_selector("head")
    if not head:
        return
    store = inject(_COMPONENT_STORE_KEY)
    for gen in store.components.values():
        cid = gen._id
        css = gen.scoped_style
        if css and not dom.query_selector(f'style[data-webcompy-cid="{cid}"]'):
            el = dom.create_element("style")
            el.setAttribute("data-webcompy-cid", cid)
            el.textContent = css
            head.appendChild(el)
```

**Alternatives considered:**
- **Hook in `LazyComponentGenerator._resolve()`**: Catches lazy loads immediately but creates a layering violation (router module touching DOM). Doesn't catch deferred registrations.
- **Hook in `ComponentStore.add_component()`**: Clean separation but requires callback registration infrastructure. Over-engineered for a single use case.
- **Hook in `ComponentGenerator._try_register()`**: Same layering issues as lazy resolve hook.

**Rationale:** `_render()` is the natural reconciliation point — it's already where the framework synchronizes state with DOM, and where the current `__loading`-guarded injection lives. The cost is negligible (10-50 components, one querySelector per component).

**Migration note:** `_reconcile_scoped_styles()` is initially implemented on `AppDocumentRoot` (Task 2) for immediate bug-fix value. In Task 6, when `HeadElement` is introduced, the method moves to `HeadElement` and the `AppDocumentRoot` copy is removed. This two-phase approach allows the CSS injection fix to ship independently of the larger HeadElement refactor.

### Decision 3: Replace `style` property with `scoped_styles` dict

`AppDocumentRoot.style` (concatenated CSS string) is replaced with `scoped_styles: dict[str, str]` mapping `cid → CSS string`, sorted by cid for deterministic ordering. `WebComPyApp` forwards `scoped_styles` as a property, replacing the previous `style` forwarding.

**Alternatives considered:**
- **Keep `style` and add `scoped_styles`**: Unnecessary duplication. Every consumer (SSG `_html.py`, browser `_reconcile_scoped_styles`) switches to the dict form.
- **List of tuples**: Dict provides natural dedup and lookup.

**Rationale:** Dict provides `cid → CSS` lookup for both SSG template generation and browser `_reconcile_scoped_styles`. Sorting by cid ensures deterministic HTML output.

### Decision 4: SSG pre-resolve of all lazy routes

Before the per-route SSG loop, all `LazyComponentGenerator` entries in routes are pre-resolved via `_preload()`. This ensures `_register_deferred_components()` in `WebComPyApp.__init__` picks up all component generators into `ComponentStore`.

```python
# In generate_static_site()
if app.router_mode == "history" and app.routes:
    for p, _, _, _, page in app.routes:
        if hasattr(page, '_preload'):
            page._preload()
    # ... existing per-route loop
```

**Alternatives considered:**
- **Collect all styles before the loop and inject separately**: Would require extracting CSS outside the normal ComponentStore → scoped_styles pipeline. More code, more edge cases.
- **Single ComponentStore for all routes**: Would violate per-route isolation (different pages would share ComponentStore state).

**Rationale:** Minimal change — one loop added before the existing generate loop. All component generators end up in `_unregistered_generators` and are picked up by `_register_deferred_components()` into the app's `ComponentStore`.

### Decision 5: HeadElement VDOM class

Introduce `HeadElement` as a special-purpose `ElementWithChildren` subclass that represents the `<head>` element. It manages title, meta, link, script, and style elements as VDOM children.

```python
class HeadElement(ElementWithChildren):
    def __init__(self, head_props: HeadPropsStore, ...):
        ...
        # Build initial children from head_props
        self._children = [
            TitleElement(head_props.title),
            *[MetaElement(k, v) for k, v in head_props.head_meta.value.items()],
            ...
        ]

    def _render(self):
        # In browser: reconcile VDOM children with actual <head> DOM
        # In server: no-op (SSG reads children via render_html())
        ...
```

`AppDocumentRoot` delegates head management to `HeadElement` instead of imperative methods. `_html.py`'s `generate_html()` renders head from `HeadElement.render_html()` instead of manually constructing `_HtmlElement` fragments.

**Alternatives considered:**
- **Keep imperative head + add style reconciliation**: Simpler but doesn't address the SSG/browser split. Head VDOM is scoped here because scoped CSS naturally integrates into it.
- **Full reactive head**: Individual meta/link/script as reactive VDOM nodes with fine-grained diffing. Over-scoped for this change; full reconciliation is sufficient.

**Rationale:** Unifies SSG and browser head rendering. Scoped CSS `<style>` elements become natural children of `HeadElement`, eliminating the special-case handling in both `_html.py` and `AppDocumentRoot._render()`. The two-phase migration (Task 2: `AppDocumentRoot._reconcile_scoped_styles()` → Task 6: `HeadElement` style children) ensures the CSS injection fix is available before the HeadElement refactor completes.

### Decision 6: `*[hidden]` base rule stays in `id="webcompy-scoped-styles"`

The `*[hidden]{display:none}` utility rule remains in a dedicated `<style id="webcompy-scoped-styles">` element. This is not scoped to any component — it's a framework-wide utility.

**Rationale:** This rule is not component-specific. Keeping it in its own element with the original `id` provides backward compatibility for existing SSR pages during migration.

## Risks / Trade-offs

- **[Risk] SSG pre-resolve causes all lazy modules to be imported**: In normal SSG, lazy routes are only resolved when their specific page is generated. Pre-resolving all imports increases memory usage slightly. → **Mitigation**: The number of lazy routes in typical apps is small (docs_app has 7). All modules are already imported during the SSG loop — pre-resolving just changes the timing, not the total set of imports.

- **[Risk] HeadElement changes the head rendering pipeline**: Previously `_html.py` constructed head HTML directly from `app.head` properties. With HeadElement, the rendering goes through VDOM. → **Mitigation**: HeadElement's `render_html()` produces identical output to the current manual construction. E2E tests verify.

- **[Trade-off] Component styles are never removed**: Even if a component is unregistered or its route is navigated away from, its `<style data-webcompy-cid="...">` stays in the DOM. → **Acceptable**: CSS is small (a few KB total). Removing styles would require tracking component lifecycle at the CSS level, which is unnecessary complexity.

## Migration Plan

1. Implement changes in `feat/scoped-css-per-component` branch
2. No user-facing API changes except `AppDocumentRoot.style` → `scoped_styles`
3. `app.set_head()` / `app.set_title()` remain through delegation
4. Merge to `main`, then merge `main` into `feat/render-context`

## Open Questions

- HeadElement scope: Should it also handle plugin-provided head scripts, or should those remain injected by `_html.py`? → **Recommendation**: HeadElement handles core framework head content; plugin scripts stay in `_html.py` as they're generated externally.

## Phasing

**Phase 1** (this change): HeadElement manages core framework head content — `<title>`, `<meta>`, `<link>`, `<style>` (including scoped component styles). Plugin-provided scripts remain in `_html.py`. This keeps the scope focused on scoped CSS and head VDOM unification without coupling to the plugin system.

**Phase 2** (future): Plugin head content may be integrated into HeadElement once the plugin system stabilizes and a clear interface for plugin-provided head entries is defined.
