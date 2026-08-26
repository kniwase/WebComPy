# Delta: json-rpc

## ADDED Requirements

### Requirement: The typed browser client shall support RPC middleware on HTTP transports

The HTTP JSON-RPC client paths (`call`, `notify`, `batch`, SSE streaming) SHALL invoke registered `RpcMiddleware` around dispatch. Middleware SHALL observe procedure name, typed params before encoding, mutable per-call headers, and result type; mutated values SHALL affect envelope encoding and request headers respectively.

#### Scenario: Auth header middleware

- **WHEN** a middleware adds an `Authorization` header and a call is dispatched
- **THEN** the outgoing POST carries both the added header and `Content-Type: application/json`

### Requirement: Transport headers shall be a merge point preserving Content-Type

Per-call headers contributed by middleware SHALL be merged onto the fixed transport headers at the single HTTP boundary of the client. `Content-Type` SHALL remain forced to `application/json` after merging.

#### Scenario: Content-Type cannot be clobbered

- **WHEN** middleware sets `ctx.headers["Content-Type"] = "text/plain"`
- **THEN** the outgoing request still sends `Content-Type: application/json`
