# Tasks: feat-docs-advanced-realtime-rpc

## 1. State & bridge pages

- [ ] 1.1 Rework `readonly_signal.md` to the Advanced structure (when-to-use vs `use_state`, event-bridge recipes, no-transfer note)
- [ ] 1.2 Rework `signal_stream.md` (+ cell-vs-occurrence routing table at top; links to event-source/websocket recipes)

## 2. Connection pages

- [ ] 2.1 Rework `event_source.md` (shared registry, per-subscriber queues, POST streaming, reconnect semantics; structure per design)
- [ ] 2.2 Rework `websocket.md` (reconnect backoff/jitter, `last_close`, buffering; keep the gap/refetch recipe heading stable — `typed_realtime.md` anchors into it)
- [ ] 2.3 Rework `typed_realtime.md` (message_type contract, strict decode, `.last_error`, allowlist registration on both ends)

## 3. RPC pages

- [ ] 3.1 Rework `rpc_contracts.md` as the primary RPC entry: transport routing table, `Procedure`/`batch`/`notify` recipes with server+client snippets
- [ ] 3.2 Rework `rpc.md`: HTTP transport & `RpcHttpClient`, dispatcher mount, typed decoding; move legacy registry/string-call material into the labeled appendix
- [ ] 3.3 Rework `rpc_websocket.md`: subscriptions/cursors/rejoin/`resync_required`, heartbeat; contract style
- [ ] 3.4 Write `rpc_streaming.md` (`StreamingProcedure` server generator → `RpcStream` client, states, close/cancellation, SSE-over-HTTP transport, SSR empty-stream degradation) + wrapper + manifest entry after `rpc-websocket`

## 4. Verification

- [ ] 4.0 Reorder the Advanced Usage manifest entries to the spec-required realtime block order
- [ ] 4.1 Cross-link pass: Basic counterparts and middleware/DI pages referenced per split policy; no dead anchors (TOC scan)
- [ ] 4.2 E2E: existing docs tests updated for new ordering; add `rpc-streaming` page test (title, TOC, prod + static)
- [ ] 4.3 `ruff`/`pyright`/unit suites + `webcompy generate` + docs E2E groups + `check-doc-spec-refs.py` + `openspec validate feat-docs-advanced-realtime-rpc`
