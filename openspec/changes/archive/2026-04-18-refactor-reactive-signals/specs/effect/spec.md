# Effect

## Purpose

An effect is a side-effecting function that automatically tracks its reactive dependencies and re-executes when they change. Effects replace manual `on_after_updating` / `on_before_updating` callback registration for the common case of reacting to state changes, providing automatic dependency tracking, lifecycle-bound cleanup, and consistent execution ordering. Effects are the foundation for composable stateful logic in WebComPy.

## Requirements

### Requirement: Effect shall automatically track reactive dependencies
An `effect(fn)` call SHALL execute `fn` immediately, track all reactive values read during execution, and re-execute `fn` whenever any tracked dependency changes. Dependencies SHALL be re-tracked on each execution, supporting dynamic dependency changes from conditional branching.

#### Scenario: Basic effect tracks a reactive value
- **WHEN** a developer creates `count = Reactive(0)` and `effect(lambda: print(count.value))`
- **THEN** the effect SHALL execute immediately, printing `0`
- **AND** when `count.value` is set to `1`, the effect SHALL re-execute, printing `1`

#### Scenario: Effect tracks dynamic dependencies
- **WHEN** a developer creates `flag = Reactive(True)`, `a = Reactive("A")`, `b = Reactive("B")`, and an effect that reads `a.value` when `flag.value` is True and `b.value` when `flag.value` is False
- **AND** `flag.value` is set to `False`
- **THEN** the effect SHALL re-execute
- **AND** subsequent changes to `a.value` SHALL NOT trigger the effect
- **AND** subsequent changes to `b.value` SHALL trigger the effect

### Requirement: Effect shall support cleanup callbacks
An effect function MAY return a cleanup function (or receive one via an `on_cleanup` parameter). The cleanup SHALL be called before the effect re-executes and when the effect's scope is destroyed.

#### Scenario: Cleanup on re-execution
- **WHEN** an effect registers a cleanup callback and a dependency changes
- **THEN** the cleanup callback SHALL be called before the effect re-executes
- **AND** the effect function SHALL execute after cleanup

#### Scenario: Cleanup on scope destruction
- **WHEN** a component that owns an effect scope is destroyed
- **THEN** all cleanup callbacks registered by effects in that scope SHALL be called
- **AND** all reactive graph edges (producers and consumers) created by those effects SHALL be removed

### Requirement: Effect shall support scoped lifecycle management
A `create_effect_scope()` context manager SHALL collect all effects created within it. When the scope exits (component destruction), all effects SHALL be cleaned up — their producer edges removed and cleanup callbacks invoked.

#### Scenario: Component-scoped effect cleanup
- **WHEN** a developer creates effects inside a `with create_effect_scope() as scope:` block during component initialization
- **AND** the component is later destroyed
- **THEN** calling `scope.dispose()` SHALL remove all effect dependencies from the reactive graph
- **AND** SHALL invoke all effect cleanup callbacks

#### Scenario: Nested effect scopes
- **WHEN** effect scopes are nested (a composable function creates effects within a component's scope)
- **THEN** the outer scope SHALL encompass all inner scope effects
- **AND** disposing the outer scope SHALL clean up all nested effects

### Requirement: Effect execution shall be batched in browser context
In a browser environment, multiple synchronous reactive changes within a single event loop tick SHALL trigger only one effect execution per effect, after all changes have settled. In a non-browser (SSG) environment, effects SHALL execute synchronously.

#### Scenario: Multiple synchronous changes batched
- **WHEN** a developer sets `a.value = 1`, then `a.value = 2` in the same synchronous block
- **THEN** an effect depending on `a` SHALL execute only once with `a.value == 2`
- **AND** the effect SHALL NOT execute for the intermediate value `1`

#### Scenario: SSG synchronous execution
- **WHEN** effects are created in a non-browser environment (SSG)
- **THEN** effects SHALL execute synchronously after dependency changes
- **AND** no `setTimeout` batching SHALL be applied