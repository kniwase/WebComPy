# Delta: router

## ADDED Requirements

### Requirement: RouterPage shall support nested children

`RouterPage` SHALL accept an optional `children: list[RouterPage]` (recursive). Child paths SHALL be joined under the parent path (`/docs` + `/guide` → `/docs/guide`). A child with path `""` SHALL be the index route, rendered when the parent path matches exactly. A parent page that has `children` SHALL NOT be rendered as a leaf itself; a bare parent-path request with no index child SHALL fall through to the router-level default. Flat page definitions (no `children`) SHALL behave exactly as before.

#### Scenario: Joined paths
- **WHEN** a page `{path: "/docs", component: DocsLayout, children: [{path: "/guide", component: GuidePage}]}` is defined and the URL is `/docs/guide`
- **THEN** the match chain SHALL be `[DocsLayout, GuidePage]`

#### Scenario: Index route
- **WHEN** `/docs` has an index child `{path: "", component: DocsIndex}` and the URL is `/docs`
- **THEN** the match chain SHALL be `[DocsLayout, DocsIndex]`

#### Scenario: Bare parent without index falls to default
- **WHEN** `/docs` has children but no `""` index child and the URL is exactly `/docs`
- **THEN** the router-level default SHALL be rendered

#### Scenario: Flat routes unchanged
- **WHEN** pages are defined without `children`
- **THEN** matching, rendering, and context SHALL behave exactly as single-level chains

### Requirement: RouterView shall render its chain level by ancestor depth

`RouterView` SHALL determine its depth by counting `RouterView` ancestors in the element tree (computed once in `_on_set_parent`). A depth-N `RouterView` SHALL render the component at chain level N of the current match. If the chain has N or fewer levels, the `RouterView` SHALL render nothing (not an error). Multiple `RouterView`s at the same depth SHALL each render their level of the single current match.

#### Scenario: Layout with nested view
- **WHEN** the URL is `/docs/guide` matching chain `[DocsLayout, GuidePage]`
- **THEN** the root `RouterView` (depth 0) SHALL render `DocsLayout`
- **AND** the `RouterView` inside `DocsLayout` (depth 1) SHALL render `GuidePage`

#### Scenario: View deeper than chain renders empty
- **WHEN** a depth-2 `RouterView` exists but the match chain has 2 levels
- **THEN** it SHALL render nothing and SHALL NOT raise

### Requirement: Chain levels shall be reused only on identical match

For each chain level, the mounted component instance SHALL be preserved across a navigation only when the level's route record, the accumulated `path_params` (levels 0..N), and the `query` dict are all identical to the previous navigation. Otherwise, that level and all deeper levels SHALL be destroyed and re-created. Preservation SHALL use signal identity (the same instance object), so no re-render or setup re-execution occurs for preserved levels. When a level is re-created, its descendants SHALL NOT be instantiated transiently before the remounting ancestor destroys the old subtree — each level SHALL be re-created at most once per navigation.

#### Scenario: Sibling navigation preserves parent
- **WHEN** navigating from `/docs/guide` to `/docs/api` (chain level 0 identical: `DocsLayout`, no params, same query)
- **THEN** the `DocsLayout` instance SHALL be preserved (its state, scroll, and open UI persist)
- **AND** level 1 SHALL be destroyed and re-created as `ApiPage` (setup runs)

#### Scenario: Param change remounts the level
- **WHEN** navigating from `/docs/api/x` to `/docs/api/y` with route `/docs/api/{name}`
- **THEN** level 0 (`DocsLayout`) SHALL be preserved (its accumulated params are unchanged)
- **AND** level 1 (`ApiPage`) SHALL be destroyed and re-created with fresh context (setup re-runs)

#### Scenario: Query change remounts
- **WHEN** navigating from `/docs/guide?tab=a` to `/docs/guide?tab=b`
- **THEN** the level rendering `GuidePage` SHALL be remounted (query is part of context identity)

#### Scenario: Ancestor param change remounts descendants
- **WHEN** navigating from `/users/1/docs` to `/users/2/docs`
- **THEN** the `/users/{uid}` level and ALL deeper levels SHALL be remounted

#### Scenario: Descendant levels are re-created once per navigation
- **WHEN** a query or ancestor-param change remounts an ancestor level
- **THEN** the ancestor and each descendant level SHALL be re-created exactly once
- **AND** no transient duplicate instance SHALL be created for any descendant level (setup SHALL NOT run twice for the same navigation)

### Requirement: RouterContext path_params shall accumulate ancestor params

The `RouterContext` passed to a level-N component SHALL contain `path_params` merged from levels 0 through N (child wins on name collision). `path` SHALL be the full current path; `query` and `params` (state) SHALL be navigation-level values shared by all levels.

#### Scenario: Child sees ancestor param
- **WHEN** the URL is `/users/42/docs/7` matching `/users/{uid}` → `/docs/{doc_id}`
- **THEN** the leaf component's `context.props.path_params` SHALL contain both `uid` (`"42"`) and `doc_id` (`"7"`)

### Requirement: Nested routes shall integrate with lazy loading, hooks, and SSG

Lazy components (`lazy()`) SHALL be allowed at any tree level; preloading SHALL traverse the whole tree. Router hooks SHALL fire once per navigation (not per level). `Router.__routes__` SHALL remain a flat list of full leaf paths in the existing 5-tuple shape so that static site generation enumerates all nested paths without changes to the CLI.

#### Scenario: Lazy child preloads on hover
- **WHEN** a child route uses `lazy("app.pages.guide:GuidePage", __file__)` and a `RouterLink` to its full path is hovered
- **THEN** the child module SHALL preload (existing hover behavior, resolved through the flattened routes)

#### Scenario: Hooks fire once
- **WHEN** navigating from `/docs/guide` to `/docs/api`
- **THEN** `before_route_change` and `after_route_change` SHALL each fire exactly once

#### Scenario: SSG renders nested paths
- **WHEN** `webcompy generate` runs with history-mode nested routes `/docs` → `["", "/guide"]`
- **THEN** static HTML SHALL be produced for `/docs/` and `/docs/guide/`, each with the full chain rendered
