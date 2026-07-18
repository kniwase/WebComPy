## Why

Two element-system refactors needed before the template engine:

**`ChildNode` type widening**: The `ChildNode` type alias in `webcompy/elements/generators.py` is declared as `ElementBase | TextElement | MultiLineTextElement | NewLine | SignalBase | str | None`. However, `DynamicElement` subclasses (`SwitchElement`, `RepeatElement`) extend `ElementWithChildren -> ElementAbstract`, NOT `ElementBase`. This creates a latent type gap: the return values of `switch()` and `repeat()` (both `DynamicElement`) are technically not valid `ChildNode` members under strict type checking. The alias only appears to work because `MultiLineTextElement` (a `RepeatElement` subclass) was added explicitly while its parent `RepeatElement` and sibling `SwitchElement` were omitted — an inconsistency.

**`_refresh_sync` common helper**: `_switch.py:76-92` and `_repeat.py:144-160` contain virtually identical `_refresh_sync` implementations (the nest_asyncio + loop.run_until_complete sync wrapper). The upcoming `MarkdownForElement` (template engine) would create a third copy. Extracting a shared `_run_refresh_sync` helper in `_dynamic.py` and reducing Switch/Repeat to one-line delegations eliminates duplication and keeps the async-invariant pattern in one place.

The upcoming template engine introduces `FragmentElement` (another `DynamicElement`) and `MarkdownForElement`. Rather than patching the `ChildNode` alias per-element and duplicating the `_refresh_sync` pattern, this change addresses both proactively.

## What Changes

### Part 1: ChildNode type widening
- Consolidate `ChildNode` from `ElementBase | TextElement | MultiLineTextElement | NewLine | SignalBase[Any] | str | None` to `ElementAbstract | SignalBase[Any] | str | None`
- `TextElement`, `MultiLineTextElement`, and `NewLine` are removed from the explicit union because they are all `ElementAbstract` subclasses (subsumed)
- This is a type widening (`ElementBase` is a subset of `ElementAbstract`); all previously accepted values remain valid, and `SwitchElement` / `RepeatElement` / future `FragmentElement` become correctly typed

### Part 2: `_refresh_sync` common helper
- Extract a `_run_refresh_sync(refresh: Callable[..., Awaitable[None]], *args: Any) -> None` helper in `webcompy/elements/types/_dynamic.py`
- The helper encapsulates the nest_asyncio + loop.run_until_complete sync wrapper (currently duplicated verbatim in `_switch.py:76-92` and `_repeat.py:144-160`)
- Reduce `SwitchElement._refresh_sync` and `RepeatElement._refresh_sync` to one-line delegations: `_run_refresh_sync(self._refresh, *args)`
- `MarkdownForElement` (template engine Change 6) will use the same helper instead of creating a third copy

## Capabilities

### New Capabilities
_None_

### Modified Capabilities
- `elements`: `ChildNode` type alias widened to `ElementAbstract` base, subsuming text/newline element types and covering all `DynamicElement` subclasses

## Known Issues Addressed
_None — proactively resolves a latent type gap surfaced during the template-engine proposal review_

## Non-goals
- Unifying `ChildNode` and `ElementChildren` into a single alias (they are structurally identical after this change; consolidation deferred to avoid churn)
- Changing runtime behavior of `_create_child_element` or `_is_patchable` (purely a type-alias change)
- Adding `ChildNode` to the public `webcompy.elements` export surface

## Impact

- **Modified files**: 
  - `packages/webcompy/src/webcompy/elements/generators.py` — `ChildNode` alias (line 66); adjust imports (add `ElementAbstract`, drop `ElementBase` if no other usage)
  - `packages/webcompy/src/webcompy/elements/types/_dynamic.py` — add `_run_refresh_sync` helper function
  - `packages/webcompy/src/webcompy/elements/types/_switch.py` — `_refresh_sync` reduced to one-line delegation
  - `packages/webcompy/src/webcompy/elements/types/_repeat.py` — `_refresh_sync` reduced to one-line delegation
- **Type-only change** (Part 1): No runtime behavior change. `pyright` is the verification gate.
- **Pure refactor** (Part 2): Behavior-preserving extraction. `pytest` confirms no regressions.
- **No breaking changes**: Type widening is backward-compatible.

## Dependencies

- **Depends on**: None
- **Required by**: `feat-template-control-flow` (FragmentElement relies on `ChildNode` accepting `DynamicElement`), `feat-template-markdown-for-expansion` (MarkdownForElement uses `_run_refresh_sync` helper)
- **Recommended implementation order**: First (0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7)
