# Proposal: feat-docs-advanced-realtime-rpc

## Why

The realtime and RPC pages in Advanced Usage are framework-internal notes: they accurately describe behaviors (shared registries, reconnection, cursors) but read as condensed spec prose rather than task-oriented user docs, and `rpc.md` still mixes the pre-contracts `register`/`call` era with the #274 declarative contract surface. Advanced users evaluating WebComPy for chat/live apps need cookbook-style guidance with copyable patterns.

## What Changes

- Rework the nine realtime/RPC pages in Advanced Usage into a consistent structure (when-to-use → setup → pattern recipes → behavior notes → pitfalls): `event-source`, `websocket`, `typed-realtime`, `signal-stream`, `readonly-signal` plus the RPC quartet `rpc` (HTTP transport & `RpcHttpClient`), `rpc-contracts` (declarative `Procedure`/`StreamingProcedure`/`Subscription` — promoted as the primary RPC entry), `rpc-websocket` (subscriptions, rejoin, heartbeat), and a new `rpc-streaming` page (`RpcStream`, SSE-over-HTTP streaming, cancellation).
- Lead with the contract API (#274) everywhere; move the low-level `ProcedureRegistry.call`/string-method form to a "manual transport" appendix so contract-first readers aren't misled.
- Add a decision guide at the section head: `use_state` vs `use_readonly_signal` vs signal streams (cell vs occurrence semantics) and HTTP vs SSE vs WebSocket vs RPC routing table (when each fits).
- Add cross-links to the Basic counterparts per the split policy, and to the middleware pages for auth-header injection patterns.
- E2E: keep existing docs tests; add anchor/TOC checks for the new `rpc-streaming` page.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: Advanced realtime ordering and the decision-guide requirement; new page in the manifest.

## Impact

- `docs_app/documents/`: edits to 9 existing `.md` + 1 new `rpc_streaming.md`; new manifest entry; `docs_app/pages/document/` wrapper for the new page
- Specs referenced while writing (not modified): realtime and RPC specs; no package changes

## Known Issues Addressed

Mitigates docs drift where pre-contract RPC examples (`register`/`call` tuples) mislead against the #274 breaking change.

## Non-goals

- New demo apps for realtime (Examples ③-9 covers RPC mock demos)
- Covering WebSocket transport beyond JSON-RPC (that's the composable pages' scope)
- Server-side deployment guides (③-8)
