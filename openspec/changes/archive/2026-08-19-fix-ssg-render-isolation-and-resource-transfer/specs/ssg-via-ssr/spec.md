## ADDED Requirements

### Requirement: Generated pages SHALL be independent of route generation order

The HTML output of each generated route — including the scoped-style elements in the `<head>` and the hydration transfer payload — SHALL NOT depend on which other routes were generated before it. Generating the same site twice, or generating a subset of routes, SHALL produce identical per-route output (aside from build metadata that is intentionally shared, such as version hashes). Any state accumulated while generating one route SHALL NOT leak into another route's output.

#### Scenario: Page generated first vs. last
- **WHEN** a site with routes `/a` and `/b` is generated in the order `/a`, `/b`
- **AND** the same site is generated in the order `/b`, `/a`
- **THEN** the HTML for `/a` SHALL be byte-identical in both runs
- **AND** the HTML for `/b` SHALL be byte-identical in both runs

#### Scenario: Layout-only component styles on later pages
- **WHEN** a nested route uses a lazily loaded layout that imports additional styled components
- **THEN** pages under that route SHALL contain those components' scoped styles whether they are generated first, in the middle, or last

#### Scenario: Payload does not accumulate across routes
- **WHEN** route `/a` loads resource `a.md` and route `/b` loads resource `b.md` during SSG with the default transfer mode
- **THEN** `/b`'s payload SHALL NOT contain `a.md`, regardless of generation order
