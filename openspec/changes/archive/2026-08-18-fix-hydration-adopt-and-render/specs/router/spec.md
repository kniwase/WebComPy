# Router — Hydration "Adopt & Render" Deltas

## ADDED Requirements

### Requirement: RouterView hydration shall adopt prerendered route content

During browser hydration, `RouterView._hydrate_node()` SHALL create the routed component for the current match (as its render does) and SHALL hydrate it through the standard `DynamicElement` hydration pass: the child (route boundary → page component) SHALL be adopted from the prerendered DOM when the structures match, and its hydration render SHALL be scheduled through the `ASYNC_SCHEDULER_PORT_KEY`. Prerendered route content SHALL NOT be removed from the DOM by hydration's node-count cleanup: because hydration creates the routed component before the parent container reconciles its child counts, the route content SHALL be accounted for and preserved.

#### Scenario: Sync route page SSR nodes survive hydration
- **WHEN** the browser hydrates an SSR page whose route component is synchronous
- **THEN** the prerendered DOM nodes of the route subtree SHALL be adopted (remain in the document)
- **AND** the route component's hydration render SHALL complete its reactive setup

#### Scenario: Async route page SSR nodes survive hydration
- **WHEN** the browser hydrates an SSR page whose route component is async (`await` during setup, e.g., markdown loading)
- **THEN** the prerendered route DOM SHALL remain in the document while the async setup resolves
- **AND** after resolution, the prerendered nodes SHALL be adopted (lazily) rather than removed and rebuilt
- **AND** no removal of the route content SHALL occur during the hydration pass itself

#### Scenario: Route content is present when the loading indicator is removed
- **WHEN** `app.run()` hydrates a page and the scheduler drain runs before loading-indicator removal
- **THEN** the routed content SHALL already be in the DOM at the moment the loading indicator is removed

### Requirement: Hydrated route components shall complete setup via the hydration render

The hydration render of a route component SHALL execute the component's render path (including lifecycle hook registration and any `use_async`/`use_computed` wiring NOT restored from the transfer payload) on top of the adopted DOM, preserving the interactive-update guarantee that led nested-routes to schedule renders explicitly. Adopted (mounted) state SHALL NOT cause the hydration render to be skipped.

#### Scenario: Interactive updates work on an adopted hydrated page
- **WHEN** a route component's SSR DOM was adopted during hydration
- **AND** a user interaction changes a signal-driven part of the page after hydration
- **THEN** the DOM SHALL update reactively (no silently dead controls)

#### Scenario: on_before_rendering/on_after_rendering fire once during hydration render
- **WHEN** a route component defines `on_before_rendering` / `on_after_rendering` hooks
- **AND** its SSR DOM was adopted during hydration
- **THEN** the hooks SHALL fire exactly once for the hydration render