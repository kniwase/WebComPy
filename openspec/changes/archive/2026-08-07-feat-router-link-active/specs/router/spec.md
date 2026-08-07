# Delta: router

## ADDED Requirements

### Requirement: RouterLink shall support active-state styling

`RouterLink` SHALL accept optional keyword arguments `active_class: str | SignalBase[str] | None = None` and `exact: bool = False`. While the link's target path matches the current route, the rendered anchor SHALL include the active class in its `class` attribute and SHALL carry `aria-current="page"`; when not active, neither SHALL be present. When `active_class` is `None`, the link SHALL render exactly as before (no subscription, no matching).

Matching SHALL compare path portions only (query string ignored). With `exact=False` (default), a target `T` matches current path `C` when `C == T` or `C` starts with `T + "/"`. Both `C` and `T` SHALL be normalized (leading slash, no trailing slash) before comparison, so `to="/docs"` matches the current path `/docs/`. The root target `/` SHALL always be matched exactly. With `exact=True`, only `C == T` matches. When no route matches (`current_match is None`), the link SHALL NOT be active.

Active state SHALL be reactive: after any client-side navigation, affected links SHALL update their attributes without user code. The initial SSR/SSG render SHALL compute active state from the request path so generated HTML is already correct.

#### Scenario: Prefix match activates parent link
- **GIVEN** a `RouterLink` with `to="/docs"` and `active_class="active"`
- **WHEN** the current route is `/docs/getting-started`
- **THEN** the anchor's `class` SHALL include `active`
- **AND** the anchor SHALL carry `aria-current="page"`

#### Scenario: Segment boundary prevents false positives
- **GIVEN** a `RouterLink` with `to="/docs"` and `active_class="active"`
- **WHEN** the current route is `/docsx`
- **THEN** the anchor SHALL NOT include `active` and SHALL NOT carry `aria-current`

#### Scenario: Trailing slash normalization
- **GIVEN** a `RouterLink` with `to="/docs"` and `active_class="active"`
- **WHEN** the current route is `/docs/` (trailing slash)
- **THEN** the anchor SHALL include `active`

#### Scenario: Root link matches exactly
- **GIVEN** a `RouterLink` with `to="/"` and `active_class="active"`
- **WHEN** the current route is `/about`
- **THEN** the anchor SHALL NOT include `active`

#### Scenario: Exact matching
- **GIVEN** a `RouterLink` with `to="/docs"`, `active_class="active"`, and `exact=True`
- **WHEN** the current route is `/docs/getting-started`
- **THEN** the anchor SHALL NOT include `active`

#### Scenario: Query string ignored
- **GIVEN** a `RouterLink` with `to="/search"` and `active_class="active"`
- **WHEN** the current route is `/search?q=python`
- **THEN** the anchor SHALL include `active`

#### Scenario: Reactive update on navigation
- **GIVEN** two links with `active_class`, pointing to `/a` and `/b`, rendered while on `/a`
- **WHEN** the user navigates to `/b`
- **THEN** the `/a` link SHALL lose the active class and `aria-current`
- **AND** the `/b` link SHALL gain them

#### Scenario: SSR renders correct initial state
- **GIVEN** a page with a `RouterLink` to `/about` with `active_class="active"`
- **WHEN** the page is server-rendered for request path `/about`
- **THEN** the generated HTML SHALL already include `class` containing `active` and `aria-current="page"`
