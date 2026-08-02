## ADDED Requirements

### Requirement: ElementAbstract shall expose a _children attribute for uniform tree-walking

`ElementAbstract` (the common root of `Element`, `Component`, `TextElement`, and all `DynamicElement` subclasses) SHALL declare a `_children: list[ElementAbstract]` attribute. Because framework tree-walking code (Suspense async collection, hydration resolution checks, dynamic-element reconciliation) operates on values typed as `ElementAbstract` and must recurse into child nodes, the `_children` attribute SHALL be reachable through the base type rather than only on specific subclasses. Leaf node types (e.g. `TextElement`) SHALL inherit an empty `_children` list that is never mutated. This declaration SHALL NOT change any runtime child-management behavior; it only reflects the existing runtime invariant in the static type system.

#### Scenario: Suspense collects pending async components through the base type
- **WHEN** `SuspenseElement._collect_pending_coroutines` walks an element subtree typed as `ElementAbstract`
- **THEN** it SHALL be able to read `element._children` on any node without an `isinstance` narrowing or `hasattr` bypass
- **AND** `uv run pyright` SHALL report no `reportAttributeAccessIssue` warning for the access

#### Scenario: Hydration resolution check recurses through the base type
- **WHEN** `SuspenseElement._hydrate_node` checks whether all descendants have resolved hydration data
- **THEN** the recursion SHALL read `element._children` through the `ElementAbstract` annotation
- **AND** leaf nodes (e.g. `TextElement`) SHALL expose an empty `_children` list so iteration is a no-op

#### Scenario: Leaf element inherits an empty non-mutated children list
- **WHEN** a `TextElement` instance is created
- **THEN** it SHALL inherit the class-level `_children` default of `[]`
- **AND** no framework code SHALL append to or replace a leaf element's `_children`
