# Delta: app-config

## ADDED Requirements

### Requirement: WebComPyAppConfig shall accept a scroll_restoration flag

`WebComPyAppConfig` SHALL accept a `scroll_restoration: bool` field defaulting to `True`. When `True`, browser apps SHALL exhibit the scroll-restoration behavior defined by the `scroll-restoration` capability. When `False`, the framework SHALL NOT mutate `history.scrollRestoration` and SHALL NOT save or restore scroll positions.

#### Scenario: Default enabled
- **WHEN** an app is created without specifying `scroll_restoration`
- **THEN** scroll restoration SHALL be active in the browser

#### Scenario: Explicit opt-out
- **WHEN** an app is created with `scroll_restoration=False`
- **THEN** no scroll management SHALL occur and the browser's native behavior SHALL be left untouched
