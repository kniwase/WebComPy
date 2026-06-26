# App Delta

## ADDED Requirements

### Requirement: WebComPyApp shall provide append_style

The framework SHALL provide `WebComPyApp.append_style(content: str | Computed[str])` method. The method SHALL register a CSS style string or reactive computed with the head element. The method SHALL be callable from the active render context OR be deferred if called outside (matching the existing `append_link` and `append_script` semantics).

#### Scenario: Calling append_style with the active context
- **WHEN** `app.append_style(content)` is called while a render context is active
- **THEN** the framework SHALL delegate to the render context's `append_style`

#### Scenario: Calling append_style without an active context
- **WHEN** `app.append_style(content)` is called before `create_render_context()`
- **THEN** the framework SHALL append the call to `_deferred_ops`
- **AND** the call SHALL be applied when `create_render_context()` runs
