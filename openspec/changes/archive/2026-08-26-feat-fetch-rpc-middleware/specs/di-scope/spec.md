# Delta: di-scope

## ADDED Requirements

### Requirement: Middleware registries shall follow DI scope lifecycle

Fetch and RPC middleware registries SHALL be provided per render context like ports: created fresh at context initialization, resolved through the active `DIScope`, and disposed with their scope. Additive registration through the registries is the supported pattern for distributed contributors; directly providing a replacement registry or list for these keys within a live context is not a supported extension path.

#### Scenario: Per-request isolation of registrations

- **WHEN** two SSR requests are rendered concurrently
- **THEN** middleware registered during one request's context initialization is invisible to the other's chain
