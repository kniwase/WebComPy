# Delta: port-abstraction

## ADDED Requirements

### Requirement: HistoryPort shall expose a navigation-classification hook

`HistoryPort` SHALL provide `set_scroll_manager(manager | None)` accepting an object with `on_push(from_path, to_path)` and `on_pop(from_path, to_path)` methods (default `None`). `HistoryPort.navigate()` SHALL invoke `on_push` exactly once per effective navigation (after the value change; same-value early-return navigations SHALL NOT invoke it). `BrowserHistoryPort`'s popstate handling SHALL invoke `on_pop` exactly once per popstate-driven navigation, on both the default dispatch path and the `set_navigation_callback` override path. When no manager is registered, behavior SHALL be identical to before.

#### Scenario: Push classification
- **WHEN** a scroll manager is registered and `navigate("/b")` changes the path from `/a`
- **THEN** `on_push("/a", "/b")` SHALL be called exactly once

#### Scenario: Pop classification
- **WHEN** a scroll manager is registered and a popstate event moves the path from `/b` to `/a`
- **THEN** `on_pop("/b", "/a")` SHALL be called exactly once

#### Scenario: Same-value navigation does not notify
- **WHEN** `navigate()` is called with the current path and identical state
- **THEN** neither `on_push` nor `on_pop` SHALL be called

#### Scenario: No manager registered
- **WHEN** navigations occur with no manager registered
- **THEN** `HistoryPort` behavior SHALL be unchanged from before this capability existed
