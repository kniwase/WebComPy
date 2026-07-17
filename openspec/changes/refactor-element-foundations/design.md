## Context

`ChildNode` (`generators.py:66`) annotates the return type of `NodeGenerator` and the `repeat()` template callbacks. Its current union explicitly lists `ElementBase`, `TextElement`, `MultiLineTextElement`, and `NewLine`. The class hierarchy is:

```
ElementAbstract (root)
├── ElementWithChildren
│   ├── ElementBase -> Element, Component
│   └── DynamicElement -> SwitchElement, RepeatElement -> MultiLineTextElement
├── TextElement
└── NewLine
```

`TextElement`, `NewLine`, and `MultiLineTextElement` are all `ElementAbstract` descendants. `ElementBase` is also an `ElementAbstract` descendant. The only members NOT covered by `ElementBase` are the `DynamicElement` subclasses. The alias explicitly added `MultiLineTextElement` (a DynamicElement) but omitted `SwitchElement` / `RepeatElement` — an inconsistency rooted in the fact that `DynamicElement` extends `ElementWithChildren` directly, not `ElementBase`, making it a sibling of `ElementBase` rather than a subclass.

## Goals / Non-Goals

**Goals:**
- Make `ChildNode` structurally correct by basing it on `ElementAbstract`
- Eliminate per-element patching of the alias for future `DynamicElement` types (e.g., `FragmentElement`)
- Extract a shared `_run_refresh_sync` helper from the duplicated code in `SwitchElement` and `RepeatElement`
- Keep all changes behavior-preserving (no runtime effect)

**Non-Goals:**
- Merging `ChildNode` and `ElementChildren` into a single alias
- Public export of `ChildNode`

## Decisions

### D1: `ElementAbstract | SignalBase | str | None`

Replace the current union with `ElementAbstract | SignalBase[Any] | str | None`. All text / newline / dynamic element types are `ElementAbstract` subclasses and are subsumed by the root.

**Rationale**: `ElementAbstract` is the common root of every renderable node (`Element`, `Component`, `TextElement`, `NewLine`, `SwitchElement`, `RepeatElement`, `MultiLineTextElement`, and future `FragmentElement`). Basing `ChildNode` on it removes the inconsistency and is future-proof — no additional type-alias edits are needed when new element types are introduced.

**Alternatives considered**: Adding `DynamicElement` to the existing union would fix `SwitchElement` / `RepeatElement` / `FragmentElement` but perpetuate the pattern of per-element patching. Widening to `ElementAbstract` is the cleanest single change.

### D2: Type widening is safe (backward compatible)

`ElementBase` is a subclass of `ElementAbstract`, so widening from `ElementBase` to `ElementAbstract` only ADDS accepted types. Every value previously valid under `ChildNode` remains valid. No call site narrows on `ChildNode` being `ElementBase`-bounded: `ChildNode` is consumed only as a return-type annotation in `NodeGenerator` and `repeat()` callbacks. Runtime dispatch uses `_create_child_element` (which is typed over `ElementChildren` = `ElementAbstract | ...`), not `ChildNode`.

### D3: Shared `_run_refresh_sync` helper in `_dynamic.py`

`_switch.py:76-92` and `_repeat.py:144-160` contain an identical sync-wrapper pattern: the `_refresh_sync` method that imports `asyncio`, detects the running event loop, handles the `ENVIRONMENT != "pyscript"` / `nest_asyncio` branch, and calls `loop.run_until_complete(self._refresh(*args))`. The only variable part is `self._refresh` (the bound async method).

Extract a module-level helper:

```python
# _dynamic.py (new)
from typing import Any, Awaitable, Callable

def _run_refresh_sync(refresh: Callable[..., Awaitable[None]], *args: Any) -> None:
    import asyncio
    from webcompy.utils._environment import ENVIRONMENT
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(refresh(*args))
    else:
        if ENVIRONMENT != "pyscript":
            import nest_asyncio
            if not getattr(loop, "_nest_asyncio_patched", False):
                nest_asyncio.apply(loop)
                loop._nest_asyncio_patched = True  # type: ignore[attr-defined]
        loop.run_until_complete(refresh(*args))
```

Switch and Repeat become:

```python
def _refresh_sync(self, *args: Any):
    _run_refresh_sync(self._refresh, *args)
```

**Rationale**: The sync wrapper is a non-trivial async pattern (imports `nest_asyncio`, handles loop state, guards against `pyscript` environment). Three copies (including the upcoming `MarkdownForElement`) create maintenance risk — a fix to this pattern would need to be propagated to all three. `_dynamic.py` is the natural home: it already imports `asyncio` and hosts module-level helpers (`_subtree_has_async_setup`, `_patch_children`, `_position_element_nodes`). The extraction is behavior-preserving (pure refactor).

**Alternatives considered**: Keeping the duplication and documenting it as known debt. This is acceptable short-term but the async pattern is exactly the kind of code that benefits from single-point maintenance. Since `MarkdownForElement` is about to add a third copy, now is the right time to consolidate.

## Risks / Trade-offs

- **[Risk] Hidden narrowing on `ElementBase`** -> Mitigation: Grep confirmed no consumer narrows `ChildNode` to `ElementBase`. `pyright` will catch any regression.
- **[Note] `ChildNode` and `ElementChildren` become structurally identical** -> Acceptable; unification is a separate, optional cleanup.
- **[Risk] `_run_refresh_sync` extraction changes behavior** -> Mitigation: The extracted function is a verbatim copy of the existing sync-wrapper body; the only change is from method call (`self._refresh(*args)`) to delegate call (`refresh(*args)`). `pytest tests/ --tb=short` confirms no regressions.

## Open Questions

None — all design decisions resolved during planning phase.
