# Design: feat-docs-advanced-realtime-rpc

## Context

#274 replaced the tuple-style RPC registration with declarative contracts (`Procedure`, `StreamingProcedure`, `Subscription`, `batch`, `notify`, transports `RpcHttpClient`/`RpcWsClient`); #270 added `RpcStream`; #264 added WS subscriptions with cursors/rejoin/heartbeat. The docs moved to Advanced URLs (③-0) but still carry prose written against the older surfaces. Realtime docs (`use_event_source`, `use_websocket`, `typed-realtime`) are current in content but spec-toned in voice.

## Goals / Non-Goals

**Goals:** contract-first RPC docs; uniform Advanced page structure; a semantics decision guide.

**Non-Goals:** new APIs, new demos, Server & Tooling deployment pages.

## Decisions

### 1. Page inventory and roles

```
Signal & state semantics:  readonly-signal | signal-stream   (bridge page = decision table)
Streaming connections:      event-source | websocket | typed-realtime
RPC:                        rpc-contracts (primary entry) | rpc (HTTP transport,
                            client, registry internals appendix) | rpc-websocket
                            (subscriptions/rejoin/heartbeat) | rpc-streaming (NEW:
                            RpcStream states, close semantics, cancellation, SSE-over-
                            HTTP transport, SSR empty-stream degradation)
Section head decision guide: appended to signal-stream? No — a dedicated short
"Realtime & RPC overview" section at the top of the category's first page
(signal-stream stays first among state-bridging) — kept simple: the overview lives
at the top of rpc-contracts (RPC routing table) and signal-stream (cell vs occurrence
table), one screen each.
```

**Why split rpc into contracts-first**: a newcomer's path is `contracts → transport`, mirroring how the API is used; the dispatcher/`ProcedureRegistry` mechanics are appendix.

### 2. Uniform Advanced page structure (extends the docs-site-documents convention)

```
lead (what + when you need it)
"When to use" — bullet list w/ link to alternative page
Setup — minimal server + client pair (both sides always shown for RPC pages)
Recipes — 2-4 copyable patterns (auth header via RpcMiddleware, batch + typed results,
          rejoin behavior, cancellation)
Behavior notes — reconnection math, queue policy, SSR/hydration degradation
Pitfalls — known traps (duplicate signals swallowed, Last-Event-ID, replay_size bounds)
Next steps — sibling links
```

### 3. Voice shift rule

Convert normative phrasing ("the registry SHALL…") to user-facing ("WebComPy keeps one shared connection…"); behavior claims must stay traceable to specs but never cite spec/change names in text (doc convention).

### 4. Server-side code samples

Every RPC recipe shows the server side explicitly (`app.rpc.bind(...)` in a Starlette host snippet mirroring ③-9's convention) — advanced users are the ones wiring real servers.

## Risks / Trade-offs

- [9 rewrites + 1 new page in one change] → grouped tasks per page; pages independent, PR can merge per group if needed.
- [Decision tables overlap with Basic pages] → tables are pointers, not tutorials; split-policy link rule applies.
- [rpc.md legacy appendix could keep confusing] → appendix clearly labeled "manual transport (rarely needed)" and no examples lead with it.

## Migration Plan

Content-only; merge after ③-0 (URLs) and ③-1 (example-form sweep) so contract examples use current `@define_component()` where components appear.

## Open Questions

None.
