## ADDED Requirements

### Requirement: ChildNode type alias shall accept all renderable node types

`ChildNode` SHALL be defined as `ElementAbstract | SignalBase[Any] | str | None`. Because `ElementAbstract` is the common root of `Element`, `Component`, `TextElement`, `NewLine`, and all `DynamicElement` subclasses (`SwitchElement`, `RepeatElement`, `MultiLineTextElement`, and future `FragmentElement`), the alias SHALL accept any renderable element node without per-type enumeration.

#### Scenario: switch() result is a valid ChildNode
- **WHEN** a `NodeGenerator` returns a `SwitchElement` (from `switch()`)
- **THEN** the return value SHALL be a valid `ChildNode` under static type checking

#### Scenario: repeat() result is a valid ChildNode
- **WHEN** a `NodeGenerator` returns a `RepeatElement` or `MultiLineTextElement`
- **THEN** the return value SHALL be a valid `ChildNode` under static type checking

#### Scenario: Future DynamicElement types are automatically covered
- **WHEN** a new `DynamicElement` subclass (e.g., `FragmentElement`) is introduced
- **THEN** it SHALL be automatically valid as a `ChildNode` without requiring an edit to the type alias

### Requirement: DynamicElement `_refresh_sync` pattern shall use a shared helper

A `_run_refresh_sync(refresh: Callable[..., Awaitable[None]], *args: Any) -> None` helper SHALL be defined in `webcompy/elements/types/_dynamic.py`. The helper SHALL encapsulate the nest_asyncio + loop.run_until_complete sync-wrapping logic. `SwitchElement._refresh_sync` and `RepeatElement._refresh_sync` SHALL delegate to `_run_refresh_sync` instead of containing their own copies of the sync-wrapper logic.

#### Scenario: SwitchElement uses shared helper
- **WHEN** `SwitchElement._refresh_sync` is called
- **THEN** it SHALL delegate to `_run_refresh_sync(self._refresh, *args)`
- **AND** the runtime behavior SHALL be identical to the pre-extraction implementation

#### Scenario: RepeatElement uses shared helper
- **WHEN** `RepeatElement._refresh_sync` is called
- **THEN** it SHALL delegate to `_run_refresh_sync(self._refresh, *args)`
- **AND** the runtime behavior SHALL be identical to the pre-extraction implementation

#### Scenario: New DynamicElement subclasses use shared helper
- **WHEN** a new `DynamicElement` subclass (e.g., `MarkdownForElement`) requires `_refresh_sync` semantics
- **THEN** it SHALL use `_run_refresh_sync(self._refresh, *args)` without duplicating the sync-wrapper logic
