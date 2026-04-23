# Design: Full Hydration — DOM-First Component Reconstruction

## Design Decisions

### D1: Hydrate only prerendered nodes from SSG output
`_hydrate_node()` walks the real DOM looking for a matching prerendered node at the expected position. If found, it adopts the node. If not found (e.g., conditional branch not rendered during SSG), it falls back to `_init_node()`. This means hydration is **granular**: some subtrees hydrate fully, some fall back to creation.

### D2: Python object construction is NOT skipped
Even when hydrating, the framework still creates all Python `Element`, `Component`, `TextElement`, and `Signal` objects. This is unavoidable because:
- Signal dependencies and callbacks must exist after hydration
- DI scopes must be created
- `on_after_rendering` hooks must be registered
- Event handlers cannot be extracted from DOM (they are Python functions)

The optimization target is the **DOM layer** only.

### D3: `_hydrate_node()` is the sole entry point for adoption
All prerendered node adoption goes through `_hydrate_node()`. This method is called instead of `_init_node()` during the initial render when the app is in hydration mode. Elements that do NOT have a matching prerendered node still call `_init_node()` + `_mount_node()` normally.

### D4: Hydration mode is automatic in the browser, off by default on server
`hydrate` defaults to `True` (browser) / `False` (server). The CLI/SSG sets `hydrate=False` for `WebComPyApp` creation, since server-side rendering builds the DOM from scratch.

### D5: `_adopt_node()` is separated for reuse
The core DOM adoption logic (set `_node_cache`, bind attributes/events/signals) is extracted into `_adopt_node()` on `ElementBase` and `TextElement`. This is the same method that `feat/switch-patch` will use for runtime DOM node reuse.

## Architecture

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
       → For elements NOT in prerendered tree:
          a. Fall back to current _init_node() + _mount_node()
     → Remove #webcompy-loading
```

## API Design

### `AppConfig` field addition

```python
@dataclass
class AppConfig:
    app_package: Path | str = "."
    base_url: str = "/"
    dependencies: list[str] = field(default_factory=list)
    assets: dict[str, str] | None = None
    profile: bool = False
    hydrate: bool = True  # NEW — default True (browser), False (server)
```

### `WebComPyApp` extension

```python
class WebComPyApp:
    def __init__(self, ..., hydrate: bool = True):
        self._hydrate = hydrate
        # ... existing init ...
```

### `_hydrate_node()` on `ElementAbstract`

```python
class ElementAbstract:
    def _hydrate_node(self) -> DOMNode:
        """Adopt an existing prerendered DOM node instead of creating a new one."""
        existing = self._get_existing_node()
        if existing and getattr(existing, "__webcompy_prerendered_node__", False):
            self._adopt_node(existing)
            return existing
        else:
            return self._init_node()
```

### `_adopt_node()` on `ElementBase`

```python
class ElementBase(ElementWithChildren):
    def _adopt_node(self, node: DOMNode) -> None:
        """Adopt an existing DOM node instead of creating a new one.

        The node is assumed to already be in the DOM at the correct position.
        Attributes, event handlers, and Signal callbacks are rebound to this element.
        """
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True

        # Attribute diff: apply current attrs, remove stale ones
        current_attrs = self._get_processed_attrs()
        existing_attr_names = set(node.getAttributeNames())
        new_attr_names = set(current_attrs.keys())
        for name in existing_attr_names - new_attr_names - WEBCOMPY_INTERNAL_ATTRS:
            node.removeAttribute(name)
        for name, value in current_attrs.items():
            if value is not None:
                existing = node.getAttribute(name)
                if existing != value:
                    node.setAttribute(name, value)
            elif name in existing_attr_names:
                node.removeAttribute(name)

        # Signal callbacks for reactive attributes
        for name, value in self._attrs.items():
            if isinstance(value, SignalBase):
                self._add_callback_node(
                    value.on_after_updating(self._generate_attr_updater(name))
                )

        # Event handlers
        self._event_handlers_added = {}
        for name, func in self._event_handlers.items():
            event_handler = _generate_event_handler(func)
            node.addEventListener(name, event_handler, False)
            self._event_handlers_added[name] = event_handler

        # DomNodeRef
        if self._ref:
            self._ref.__init_node__(node)
```

### `_adopt_node()` on `TextElement`

```python
class TextElement(ElementAbstract):
    def _adopt_node(self, node: DOMNode) -> None:
        """Adopt an existing text node."""
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True
        current_text = self._get_text()
        if node.textContent != current_text:
            node.textContent = current_text
        # Signal callback already registered in __init__
```

### `AppDocumentRoot._render()` integration

```python
class AppDocumentRoot(...):
    def _render(self):
        if self._app._hydrate and not self._rendered_children:
            # Hydration mode: try _hydrate_node() first
            for child in self._children:
                child._hydrate_node()
            # Unmatched new children fall back to _init_node() + _mount_node()
            for child in self._children:
                if not child._mounted:
                    child._render()
        else:
            # Normal non-hydration path
            for child in self._children:
                child._render()
        # Remove loading indicator (unchanged)
        ...
```

## Integration with Partial Hydration

`feat/hydration-partial` added conditional attribute/textContent writes. Hydration-full extends this by skipping `createElement`/`createTextNode` entirely and skipping `_mount_node()`.

```
Partial hydration (feat/hydration-partial):
  ├─ Reuses existing prerendered node (avoids createElement)
  ├─ Conditionally skips setAttribute for matching values
  └─ Conditionally skips textContent write for matching text
  └─ Still calls _mount_node() (appendChild — effectively no-op if already in DOM)

Full hydration (feat/hydration-full):
  ├─ Reuses existing prerendered node (avoids createElement)
  ├─ Conditionally skips setAttribute for matching values (inherited from partial)
  ├─ Conditionally skips textContent write for matching text (inherited from partial)
  ├─ Skips _mount_node() entirely (avoids appendChild/insertBefore — guaranteed no-op)
  └─ Only attaches signals and events
```

## SSG and Server-Side Behavior

- `WebComPyApp` created by SSG / `create_asgi_app()` uses `hydrate=False`.
- `_hydrate_node()` is never called, `_render()` uses the normal path.
- No HTML output changes are required for hydration support.

## Dynamic Elements (SwitchElement, RepeatElement)

- `SwitchElement`: Only the currently matching branch is present in the prerendered DOM. Non-matching branches do not have prerendered nodes and fall back to `_init_node()` + `_mount_node()`. This is correct because `_get_existing_node()` returns `None` for non-matching branches.
- `RepeatElement`: Prerendered DOM contains the items that existed at SSG time. Key-based reconciliation already handles DOM node reuse for list mutations at runtime.

## Metrics Expected

For a page with ~200 DOM nodes:

| Operation | Before (Partial) | After (Full) | Savings |
|-----------|-----------------|--------------|---------|
| createElement | ~0 (from partial reuse) | ~0 | 0 |
| createTextNode | ~0 (from partial reuse) | ~0 | 0 |
| appendChild | ~200 (from _mount_node) | ~0 | ~200 |
| insertBefore | ~0 | ~0 | 0 |
| setAttribute | up to ~M×N | up to ~M×N | 0 (same as partial) |
| addEventListener | ~50 (same) | ~50 (same) | 0 |
| Signal callback reg | ~30 (same) | ~30 (same) | 0 |

Key difference: `_mount_node()` is skipped entirely for all prerendered nodes, eliminating all `appendChild`/`insertBefore` calls during hydration. This is the last remaining DOM creation overhead after partial hydration.

## Reuse Contract (`_adopt_node`)

This is the same method that `feat/switch-patch` will call for runtime DOM node adoption. The contract is:

```
Preconditions:
  - node is a real DOMNode already attached to the DOM tree
  - node is not currently managed by another ElementAbstract instance

Postconditions:
  - self._node_cache == node
  - self._mounted == True
  - node.__webcompy_node__ == True
  - self's current attributes are synced to node
  - self's event handlers are attached to node
  - self's reactive attribute callbacks are registered
  - self's DomNodeRef (if any) is initialized

Cleanup (for old element whose node was adopted):
  - old element must call _detach_from_node() (see switch-patch design)
  - _detach_from_node removes old event handlers from node WITHOUT removing node
  - old signal callbacks are destroyed
  - old DomNodeRef is reset
```

## Rollback Path

If hydration introduces instability:
1. Set `AppConfig(hydrate=False)` to revert to the previous behavior.
2. The `_hydrate_node()` method falls back to `_init_node()` automatically when no prerendered node is found, so even with `hydrate=True`, unmatched branches work correctly.

## Dependencies

- **Depends on:** `feat/hydration-partial` — `_adopt_node` uses the same conditional attribute/text writes introduced there.
- **Depends on:** `feat/hydration-measurement` — needed to validate that the `appendChild`/`insertBefore` elimination actually reduces the measured `run_start → run_done` timing.
