# Proposal: Full Hydration — DOM-First Component Reconstruction

## Summary

Add a "full hydration" mode where the browser-side app initialization reconstructs the Python component tree by walking the pre-rendered DOM rather than creating new DOM nodes. This eliminates all DOM creation operations (createElement, createTextNode, appendChild, insertBefore) during initial hydration, replacing them with DOM node adoption and event handler attachment.

## Motivation

Even with partial hydration (skipping redundant setAttribute/textContent calls), the current hydration process still constructs the full Python component tree from scratch and then checks each DOM node against the pre-rendered tree. A full hydration mode would:

1. Skip `_init_node()` DOM creation entirely for prerendered nodes
2. Skip `Element._mount_node()` for prerendered nodes (they're already in the DOM)
3. Only attach Signal callbacks and event handlers to the existing DOM

This is the largest potential performance improvement for the DOM-mounting phase, though it requires significant architectural changes.

## Known Issues Addressed

- **No virtual DOM diffing — direct DOM manipulation only** (partially — full hydration bypasses DOM creation entirely for initial render)
- **TextElement does not hydrate pre-rendered text nodes** (fully addressed — text nodes are adopted, not recreated)

## Non-goals

- This does not reduce Python import time or Pyodide startup time (addressed by other proposals).
- This does not implement progressive hydration (hydrating components on-demand as they scroll into view).
- This does not change the SSG output beyond adding minimal metadata attributes.
- This does not change the router or component API surface.

## Dependencies

- **Depends on** `feat/hydration-measurement` — needed to validate performance gains.
- **Depends on** `feat/hydration-partial` — partial hydration is a prerequisite (content-comparison checks are needed regardless).
- **Informs** `feat/lazy-routing` — lazy routing reduces the number of components that need hydration on initial load.

## Design

### Current vs. Proposed Flow

```
CURRENT FLOW (app.run()):
══════════════════════════════════════════════════════════
  1. WebComPyApp.__init__()
     → Build entire component tree in Python
     → Each Component.__setup() runs the template function
     → Each Element/TextElement/Component object created
     → Signal graph constructed

  2. AppDocumentRoot._render()  (recursive)
     → For each element:
       a. _init_node() → check for prerendered node
          - If found & matching → reuse (set _mounted=True)
          - If NOT found → createElement/createTextNode
       b. _mount_node() → appendChild/insertBefore if not mounted
     → Remove #webcompy-loading

PROPOSED FLOW (full hydration mode):
══════════════════════════════════════════════════════════
  1. WebComPyApp.__init__(hydrate=True)
     → Build component tree in Python (same as current)
     → Template functions still run (needed for Signal graph)
     → BUT: Elements marked with _hydrate=True

  2. AppDocumentRoot._render()  (recursive)
     → For each element with _hydrate=True:
       a. _hydrate_node() → walk prerendered DOM
          - Find matching node by position + tag
          - Adopt existing node (set _node_cache, _mounted=True)
          - Attach Signal callbacks to node attributes
          - Attach event handlers via create_proxy
          - Skip all createElement/createTextNode/appendChild
     → For elements NOT in prerendered tree (e.g., conditional branches):
       a. Fall back to current _init_node() + _mount_node()
     → Remove #webcompy-loading
```

### Key Insight: Full Hydration Still Needs Python Object Construction

Even in full hydration mode, we cannot skip `Component.__setup()` because:

- Signal graphs must be constructed for reactivity to work
- Event handlers must be registered (they can't be extracted from DOM)
- DI scopes must be created for `provide`/`inject`
- `on_after_rendering` hooks must be registered

Therefore, the optimization is purely on the **DOM side** — no createElement/createTextNode/appendChild for nodes that already exist in the prerendered tree.

### Implementation Steps

#### Step 1: Add `hydrate` parameter to `WebComPyApp` and `AppConfig`

```python
@dataclass
class AppConfig:
    app_package: Path | str = "."
    base_url: str = "/"
    dependencies: list[str] = field(default_factory=list)
    assets: dict[str, str] | None = None
    hydrate: bool = True  # Default True when browser, ignored for SSG
```

When `hydrate=True` (the default in browser environment), the app will attempt full hydration of prerendered nodes. When `hydrate=False` or in SSG mode, current behavior applies.

#### Step 2: Implement `_hydrate_node()` on `ElementAbstract`

A new method that walks the prerendered DOM and adopts nodes without creating new ones:

```python
class ElementAbstract:
    def _hydrate_node(self) -> DOMNode:
        """Adopt an existing prerendered DOM node instead of creating a new one."""
        existing = self._get_existing_node()
        if existing and getattr(existing, "__webcompy_prerendered_node__", False):
            node = existing
            self._mounted = True
            # Attach event handlers to existing node
            self._event_handlers_added = {}
            for name, func in self._event_handlers.items():
                event_handler = _generate_event_handler(func)
                node.addEventListener(name, event_handler, False)
                self._event_handlers_added[name] = event_handler
            # Set up Signal callbacks for reactive attributes
            for name, value in self._attrs.items():
                if isinstance(value, SignalBase):
                    self._add_callback_node(
                        value.on_after_updating(self._generate_attr_updater(name))
                    )
            return node
        else:
            # Fallback to current behavior
            return self._init_node()
```

#### Step 3: Thread hydration through the render tree

`AppDocumentRoot` already marks prerendered nodes via `_mark_as_prerendered()`. In hydration mode, every element should use `_hydrate_node()` instead of `_init_node()` for prerendered nodes.

#### Step 4: Handle conditional content (SwitchElement, RepeatElement)

Dynamic elements that were not pre-rendered (e.g., conditional branches that don't match the SSG route) will fall back to `_init_node()` + `_mount_node()`. This already works correctly — `SwitchElement._get_existing_node()` returns `None` for non-matching branches.

### SSG Changes

The SSG output needs minimal changes to support full hydration:

1. The `__webcompy_prerendered_node__` flag is already set on all prerendered nodes
2. No new HTML attributes are needed (the existing `webcompy-component` and `webcompy-cid-*` attributes are sufficient for matching)
3. The `hidden` attribute on `AppDocumentRoot` (already used during SSG) ensures the pre-rendered content is not displayed twice

### Metrics Expected

Based on analysis of the codebase:

- For a page with ~200 DOM nodes: ~200 fewer `createElement`/`createTextNode` calls, ~200 fewer `appendChild`/`insertBefore` calls
- For a page with ~50 event handlers: ~50 `addEventListener` calls (same as current, unavoidable)
- For a page with ~30 reactive attributes: ~30 Signal callback registrations (same as current, unavoidable)

The Python-side overhead (component construction, Signal graph) remains unchanged. Expected DOM-side time savings: 30-60% of the current DOM-mounting phase.

## Specs Affected

- `elements` — adds `_hydrate_node()` method to `ElementAbstract`; updates "Pre-rendered DOM nodes shall be reused during hydration" requirement
- `app` — adds `hydrate` config option to `AppConfig`; updates "The application shall hydrate pre-rendered content" requirement; updates `WebComPyApp.__init__()` signature to accept `hydrate` parameter
- `cli` — no changes needed (SSG output format unchanged)