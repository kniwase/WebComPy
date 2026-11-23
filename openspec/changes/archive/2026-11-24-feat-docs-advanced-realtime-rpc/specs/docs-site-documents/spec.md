# Delta: docs-site-documents

## ADDED Requirements

### Requirement: The Advanced realtime and RPC pages shall be contract-first and uniformly structured

The Advanced Usage realtime block SHALL present pages in this order: `readonly-signal`, `signal-stream`, `event-source`, `websocket`, `typed-realtime`, `rpc-contracts`, `rpc`, `rpc-websocket`, `rpc-streaming`. `rpc-contracts` SHALL be the primary RPC entry point teaching the declarative contract API (`Procedure`/`StreamingProcedure`/`Subscription`, `batch`/`notify`, `bind`), with the lower-level `ProcedureRegistry`/string-method transport confined to a clearly labeled appendix on the `rpc` page. Every RPC recipe SHALL show both the server-side registration and the client-side call. Each page SHALL follow the Advanced structure (lead, when-to-use, setup, recipes, behavior notes, pitfalls, next steps) and include a routing-table section (cell vs occurrence semantics on `signal-stream`; HTTP vs SSE vs WebSocket vs RPC on `rpc-contracts`).

#### Scenario: Contract-first lead

- **WHEN** a reader opens `rpc-contracts`
- **THEN** the first examples define a `Procedure` and call it through a transport, and `register`/string-name `call` appears only in the labeled appendix on the `rpc` page

#### Scenario: Server side present in RPC recipes

- **WHEN** any RPC recipe page is read
- **THEN** each recipe includes a server-side registration snippet alongside the client snippet
