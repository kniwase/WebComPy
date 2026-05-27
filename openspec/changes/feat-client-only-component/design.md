# Design: Client-Only Component

## Context

WebComPy renders the same Python code in two environments: browser (PyScript/Emscripten) and server (CPython). Currently, developers who need browser-only content must use manual `ENVIRONMENT` checks or `switch()` with environment-based conditions. Both approaches have problems:

1. **Manual checks** scatter environment logic and don't integrate with the element tree.
2. **`switch()`** evaluates the generator function for all branches, triggering side effects in the browser branch during SSR/SSG.

The element system already has `DynamicElement` subclasses (`SwitchElement`, `RepeatElement`) that control child rendering. `ClientOnlyElement` follows this same pattern but adds environment-conditional logic.

The `feat/async-rendering-pipeline` change introduces an async `_render()` path, which `ClientOnlyElement` needs for CSR-only rendering: the browser must render children asynchronously after showing the fallback placeholder, without blocking the initial paint.

## Goals / Non-Goals

**Goals:**
- `ClientOnly` element that renders only `fallback` during SSR/SSG
- `ClientOnly` element that renders only `children` in the browser
- Children generator is never called during SSR/SSG (zero side-effect guarantee)
- During hydration, server-rendered fallback is replaced with actual children
- `fallback` parameter is optional (renders nothing during SSR if omitted)
- API follows existing element generator conventions (`switch`, `repeat`)

**Non-Goals:**
- `ServerOnly` element (could be added later)
- Async loading states or streaming SSR
- Code splitting or lazy loading
- Changing the `ENVIRONMENT` detection mechanism

## Dependency

**Requires `feat/async-rendering-pipeline`** for the async `_render()` path. `ClientOnlyElement._render()` in the browser needs to support rendering children asynchronously after the fallback has been shown. Without the async pipeline, the browser would need to synchronously replace fallback with children during initial render, which would cause a flash.

## Decisions

### Decision 1: ClientOnlyElement is a DynamicElement, not a Component

**Chosen**: `ClientOnlyElement` extends `DynamicElement` (like `SwitchElement` and `RepeatElement`), giving it direct control over when children generators are evaluated.

**Rationale**: A `DynamicElement` has no DOM node of its own — it renders its children directly into the parent. This is exactly what `ClientOnly` needs: during SSR it renders fallback children (or nothing); during hydration it replaces them with the actual children. Making it a `Component` would add an unnecessary wrapper element and prevent direct control over generator evaluation timing.

```python
class ClientOnlyElement(DynamicElement):
    def __init__(
        self,
        children: NodeGenerator,
        fallback: NodeGenerator | None = None,
    ) -> None:
        self._children_generator = children
        self._fallback_generator = fallback
        self._is_client = ENVIRONMENT == "pyscript"
        super().__init__()

    def _on_set_parent(self):
        # No signal subscriptions needed — environment is determined at init time
        pass
```

### Decision 2: SSR skips children generator evaluation entirely

**Chosen**: During SSR/SSG, `ClientOnlyElement._render()` calls only the `fallback` generator (or renders nothing if no fallback). The `children` generator is never called, ensuring zero side effects.

**Rationale**: Even calling the children generator function could trigger side effects: signal creation, DI scope changes, or async fetch scheduling. The entire point of `ClientOnly` is to avoid these costs on the server. This contrasts with `switch()`, which evaluates all branch generators to determine which branch matches.

```python
async def _render(self):
    if self._is_client:
        children = self._generate_children(self._children_generator)
    else:
        children = self._generate_fallback()
    self._children = children
    parent_node = self._parent._get_node()
    for c_idx, child in enumerate(self._children):
        child._node_idx = self._node_idx + c_idx
        await child._render()
    _position_element_nodes(self, parent_node, self._node_idx)
```

### Decision 3: Hydration replaces fallback with actual children

**Chosen**: During hydration in the browser, `ClientOnlyElement._hydrate_node()` generates the children, sets up their DOM references, and schedules async rendering via `asyncio.ensure_future(self._render())`. This is the same approach used by `SwitchElement` when branches change. `_hydrate_node()` does NOT call `child._render()` directly because `_render()` is now `async def` — calling it without `await` would produce an un-awaited coroutine.

**Rationale**: The server renders fallback content. When the browser loads, it must replace that fallback with the actual browser-only content. The `_hydrate_node()` method is the right place for this because it's called during the hydration phase of `AppDocumentRoot._render()`. Scheduling `self._render()` via `asyncio.ensure_future()` ensures the async children rendering runs on the event loop without blocking the synchronous hydration phase.

```python
def _hydrate_node(self):
    if self._is_client:
        children = self._generate_children(self._children_generator)
        self._children = children
        for c_idx, child in enumerate(self._children):
            child._node_idx = self._node_idx + c_idx
        asyncio.ensure_future(self._render())
    else:
        children = self._generate_fallback()
        self._children = children
        for c_idx, child in enumerate(self._children):
            child._hydrate_node()
```

### Decision 4: client_only() generator function API

**Chosen**: A `client_only()` function in `generators.py` matching the pattern of `switch()` and `repeat()`:

```python
from webcompy.elements import html, ClientOnly, client_only

@define_component
def MyPage(context):
    return html.DIV(
        {},
        html.H1({}, "Server Rendered Title"),
        ClientOnly(
            fallback=html.P({}, "Loading interactive part..."),
            children=lambda: InteractiveChart(),
        ),
    )
```

Or using the generator function:

```python
client_only(
    children=lambda: InteractiveChart(),
    fallback=html.P({}, "Loading..."),
)
```

**Rationale**: Both `switch()` and `repeat()` are exposed as generator functions. `client_only()` follows this convention. The `ClientOnly` class is also exported for direct use if needed (similar to `SwitchElement` / `switch`).

### Decision 5: Fallback is optional

**Chosen**: If `fallback` is `None`, `ClientOnly` renders an empty placeholder during SSR. The placeholder is a zero-width text node or an invisible comment node that occupies the correct position in the DOM for hydration to find.

**Rationale**: Not all browser-only content needs a loading indicator. Some content (analytics scripts, non-essential interactive widgets) is better rendered as nothing on the server. An empty placeholder ensures the hydration phase can still find the correct position to insert children.

### Decision 6: Environment check at initialization time

**Chosen**: `ENVIRONMENT` is checked once during `ClientOnlyElement.__init__()`. The result is stored as `self._is_client` and used for all subsequent rendering decisions.

**Rationale**: `ENVIRONMENT` is a constant (`Final`) — it never changes during a process's lifetime. Checking it once at init time avoids repeated imports and is marginally more efficient. More importantly, it makes the code's intent clear: the rendering path is determined at construction time, not at render time.

## Risks / Trade-offs

- **[Hydration mismatch]** If `ClientOnly` is misused (e.g., wrapping content that should be server-rendered), the hydration replacement will cause a visible flash. → Mitigation: This is by design — the flash is the expected behavior for content that cannot be server-rendered.
- **[Async rendering dependency]** `ClientOnlyElement` depends on the async rendering pipeline for smooth client-side rendering. Without it, the browser would synchronously replace fallback with children. → Mitigation: The dependency on `feat/async-rendering-pipeline` is explicit and documented.
- **[Testing]** `ClientOnlyElement` behavior differs fundamentally between browser and server environments. Unit tests must mock `ENVIRONMENT` to test both paths. → Mitigation: The existing `FakeBrowserDOMPort` / `ServerDOMPort` pattern already handles environment mocking.