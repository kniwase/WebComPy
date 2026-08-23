# CLI (delta)

## MODIFIED Requirements

### Requirement: The server shall expose a JSON-RPC dispatcher endpoint at a reserved prefix

When one or more RPC contracts are bound, the dev/prod server SHALL expose the JSON-RPC dispatcher endpoint at `/_webcompy-rpc` (a framework-reserved prefix under `/_webcompy`). The dispatcher SHALL be inserted as a framework-internal route via the same route-insertion point as user-provided ASGI mounts, and SHALL NOT be subject to the user-mount collision validation (which rejects `/_webcompy*` prefixes). The dispatcher MAY be registered at a custom path. When no contracts are bound, the endpoint SHALL NOT be added to the route table.

#### Scenario: Endpoint present when procedures are registered
- **WHEN** at least one contract is bound and the server is running
- **THEN** POST requests to `/_webcompy-rpc` SHALL be handled by the dispatcher

#### Scenario: Endpoint absent when no procedures are registered
- **WHEN** no contracts are bound
- **THEN** the route table SHALL NOT contain `/_webcompy-rpc`

#### Scenario: Custom dispatcher path
- **WHEN** the dispatcher is registered at a user-chosen path
- **THEN** POST requests to that path SHALL be handled by the dispatcher
