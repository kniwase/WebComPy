## ADDED Requirements

### Requirement: Async component setup failure shall run hooks registered inside the async body

When an async component setup body registers lifecycle hooks (such as `on_before_destroy` callbacks that clean up external resources like event listeners) and the async body subsequently raises or is cancelled, the component's destruction path SHALL invoke the destroy hooks registered inside that async body — not merely the hooks captured before the async body ran. The failed component SHALL be removed from its parent without re-running the failed setup, and the destruction SHALL NOT re-enter the error-handling pipeline in a way that masks the original failure.

#### Scenario: Listener cleanup registered in a failed async setup

- **WHEN** an async component setup body calls `use_window_event` (registering an `on_before_destroy` cleanup) and then raises
- **THEN** the component's `on_before_destroy` path SHALL execute the cleanup registered inside the async body
- **AND** the underlying listener cleanup SHALL run exactly once
- **AND** the component SHALL be removed from its parent without re-running the failed setup

#### Scenario: Existing cleanup ordering is preserved on success

- **WHEN** an async component setup body registers both an effect (via the effect scope) and a user `on_before_destroy` hook
- **THEN** on normal destruction the framework cleanup SHALL run before the user hook, and the async-body-registered user hook SHALL be invoked
- **AND** the change SHALL NOT alter the ordering for components whose async setup succeeds
