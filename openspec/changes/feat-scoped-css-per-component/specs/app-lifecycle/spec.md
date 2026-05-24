## MODIFIED Requirements

### Requirement: WebComPyApp shall forward AppDocumentRoot properties

`WebComPyApp` SHALL provide transparent access to frequently used `AppDocumentRoot` properties. The following properties and methods SHALL be forwarded: `routes`, `router_mode`, `set_path`, `head`, `scoped_styles`, `scripts`, `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`. The `style` forwarding property SHALL be removed (replaced by `scoped_styles`).

#### Scenario: Accessing scoped_styles
- **WHEN** a developer accesses `app.scoped_styles`
- **THEN** the result SHALL be a `dict[str, str]` mapping component cid values to CSS strings
- **AND** the dict SHALL be sorted by cid for deterministic ordering

#### Scenario: Accessing style (removed)
- **WHEN** a developer attempts to access `app.style`
- **THEN** an `AttributeError` SHALL be raised (property removed)

#### Scenario: Accessing router_mode
- **WHEN** a developer accesses `app.router_mode`
- **THEN** the result SHALL be the router mode string (or `None` if no router)