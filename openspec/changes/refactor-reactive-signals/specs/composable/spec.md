# Composable (Effect-Scoped)

This spec defines additions to the existing **composables** capability (see `openspec/specs/composables/spec.md`) that are enabled by the reactive graph redesign: automatic effect-scoped cleanup and the `effect()` primitive. The existing composable patterns (`useAsyncResult`, `useAsync`, standalone lifecycle hooks) remain unchanged — this spec adds the reactive graph mechanism that makes composable cleanup automatic rather than manual.

## ADDED Requirements

### Requirement: Effect scope shall integrate with component lifecycle context
A `create_effect_scope()` SHALL be established within the component setup context (via `_active_component_context` ContextVar). Effects created within this scope SHALL be automatically disposed when the component is destroyed, removing all producer/consumer edges from the reactive graph.

#### Scenario: Effects created inside a component are auto-cleaned on destruction
- **WHEN** a developer calls `effect(lambda: print(count.value))` inside a `@define_component` setup function
- **AND** the component is later destroyed
- **THEN** the effect's consumer edges SHALL be removed from the reactive graph
- **AND** the effect's cleanup callbacks SHALL be invoked
- **AND** changes to `count.value` SHALL NOT trigger the effect

#### Scenario: Existing composable useAsyncResult can use effect for watch cleanup
- **WHEN** `useAsyncResult` currently uses `reactive.on_after_updating(result.refetch)` plus `consumer_destroy()` with `on_before_destroy` cleanup
- **THEN** this pattern SHALL be replaced by `effect()` which automatically tracks dependencies and cleans up on scope disposal
- **AND** the `watch` parameter behavior SHALL remain identical from the user's perspective

### Requirement: Composable functions shall return reactive primitives with auto-scoped effects
A composable function SHALL create `Reactive`, `Computed`, and/or `effect` instances and return them for consumer use. When called within a component setup context, all effects created by the composable SHALL be registered in the active effect scope for automatic cleanup.

#### Scenario: Basic composable with auto-cleanup
- **WHEN** a developer writes `def use_counter(initial=0): count = Reactive(initial); ...; return count, increment`
- **AND** calls it within a component's setup function
- **THEN** `count` SHALL be a `Reactive` instance whose changes propagate to all dependents
- **AND** any effects created by `use_counter` SHALL be automatically cleaned up when the component is destroyed

#### Scenario: Composable used outside a component context
- **WHEN** a composable is called outside any effect scope (e.g., in a standalone script)
- **THEN** effects created by the composable SHALL still function
- **BUT** cleanup SHALL be the caller's responsibility via explicit `scope.dispose()` or manual `consumer_destroy()`