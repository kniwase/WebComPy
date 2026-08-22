# Tasks: feat-rpc-contracts

## 0. Preconditions

- [x] 0.1 Confirm `feat-sse-post` (`0d65127e`) and `feat-rpc-streaming` (`7e029e69`) are merged into origin/main; rebase `feat/rpc-contracts` onto the updated base — completed via rebase to `ded3285f` onto `7e029e69`
- [x] 0.2 Re-run `openspec validate feat-rpc-contracts` and `openspec validate --specs` after the rebase and confirm both pass; verify the `rpc-streaming` delta requirement titles still match the archived spec headings — verified: the `rpc-streaming` delta title `"Streaming procedures shall register from generator functions with an iterable return annotation"` matches the archived spec; no drift

## 1. Contract classes

- [ ] 1.1 Implement `Procedure[P, R]` (returns `RpcCall[P, R]`), `StreamingProcedure[P, T]`, `Subscription[P, E]` (with `replay_size=256` validation), `RpcCall[P, R]` (public `Awaitable[R]`), and the `RpcTransport` protocol in a new `webcompy/rpc/_contracts.py` (PEP 695 generics, constructor validation: reserved `_webcompy.*` names, type arguments, dataclass-only `params_type`, `Subscription(replay_size)` int>=1 bool-rejected); update `webcompy/rpc/__init__.py` exports (`Procedure`, `StreamingProcedure`, `Subscription`, `RpcCall`, `RpcTransport`, `RpcHttpClient`, `batch`); `ruff check` + `pyright` clean
- [ ] 1.2 Unit-test contract construction and delegation (typed call via `RpcCall` await, `RpcCall` is awaitable and usable in `batch`, streaming call returning `RpcStream`, subscription returning `RpcSubscription` with `replay_size`, `Procedure.notify`, reserved-name rejection, non-dataclass `params_type` rejection, non-type argument rejection) with fake transports in `tests/`

## 2. RpcHttpClient, batch, and module-function removal

- [ ] 2.1 Implement `RpcHttpClient` in `webcompy/rpc/_contracts.py` (delegates `call`/`notify`/`stream` to the internalized `_client.py` helpers, preserving SSR in-process dispatch, hydration bake, and the `rpc-streaming` SSR degradation; `subscribe` raises `RpcError`) and `batch(*calls: RpcCall, return_exceptions=False)` (free function with 1..6 heterogeneous overloads + variadic fallback, validates `RpcCall` instances via `isinstance` and shared transport instance, rejects streaming/subscription and empty calls, at least one call required; HTTP branch single POST array via `_post_envelope` with single bake entry `POST:/_webcompy-rpc:[...]`, WS branch single array frame with N Futures; `return_exceptions` controls raise vs `R|RpcError` tuple; `webcompy/rpc/_contracts.py` has no top-level import of `ProcedureRegistry`/`RpcWsClient`/`webcompy_server` — `batch` lazy-imports transports inside the function); add `RpcCall` single-await path via `transport.call` (second await raises `RuntimeError`); internalize `_client.py` (remove `call`/`notify`/`stream` from the public API and exports and delete the old `batch(Sequence[tuple[str,...]])` implementation, `batch` now exists only as typed `batch(*RpcCall)` with `*calls` varargs); `ruff check` + `pyright` clean
- [ ] 2.2 Unit-test `RpcHttpClient` and `batch` (call/notify over the fake fetch port with SSR bake assertions including batch array bake as single `POST:/_webcompy-rpc:[...]` entry, stream delegation, subscribe rejection, registry resolution from DI scope; `batch` heterogeneous `tuple[R1,R2]` inference check via `pyright`, WS batch single-frame assertion, `return_exceptions` per-call error surfacing (both `False` raise and `True` tuple), mixed-transport rejection, empty/rejected-type rejection, double-await `RuntimeError`) in `tests/`

## 3. Registry bind with signature validation

> **Dependency note**: `4.1` (dispatcher single-param decode) SHOULD land before `6.1` (dispatch migration). `3.x` and `4.x` may be implemented in parallel, but `4.1` must be merged before any dispatch-dependent tests in `6.x` are migrated.

- [ ] 3.1 Implement `ProcedureRegistry.bind(contract, impl=None)` (single method, decorator form, `isinstance` dispatch) with the three-way validation in `webcompy/rpc/_registry.py`: Procedure (non-generator, exactly one parameter whose annotation equals `params_type`, return annotation equals `result_type`), StreamingProcedure (generator + subscripted iterable annotation with matching element type, reusing the streaming detection), Subscription (async generator + subscripted `AsyncIterator[T]`/`AsyncGenerator[T, None]` with matching element type and `replay_size` flowing from `contract.replay_size` into `SubscriptionInfo`); remove `register`, `register_subscription`, and the `procedure` decorator from the public API with no alias, `__getattr__` fallback, or deprecation shim; keep `register_type_handler`; `webcompy/rpc/_contracts.py` SHALL remain the leaf import (bind lazy-imports contracts inside the method to avoid cycles); `ruff check` + `pyright` clean
- [ ] 3.2 Unit-test the bind validation matrix (parameter mismatch, result mismatch, generator bound to Procedure, non-generator bound to StreamingProcedure, unsubscripted annotations, element mismatches, unannotated subscription element, reserved names, name collisions, decorator form, `replay_size` propagation) in `tests/`

## 4. Dispatcher single-parameter decode rule

- [ ] 4.1 Update `_decode_params` in `webcompy_server/rpc/_dispatcher.py` (shared by HTTP, WS, and the subscription hub) to the contract decode rule: object-form params decode directly as the single parameter's schema (`from_json(schema, params, strict=True)`); array-form params answer `-32602`; meta handling unchanged; `_classify_stream_call` uses the same rule; `ruff check` + `pyright` clean
- [ ] 4.2 Unit-test the decode rule (object reconstruction with dataclass defaults, array rejection, meta restoration, strict extra-key rejection, WebSocket array-params rejection) in `tests/`

## 5. RpcWsClient transport re-designation and batch array handling

- [ ] 5.1 Confirm `RpcWsClient` implements the `RpcTransport` protocol surface (`call`/`notify`/`stream`/`subscribe`; single-call wire unchanged) and add WebSocket batch array handling for `batch(*RpcCall)`: single array text frame with N `Future`s correlated by `id`, `_reader` splits array responses (and the single-call dict path is preserved), `close`/`_fail_in_flight` handle N futures on disconnect; update `batch` lazy-imports `RpcWsClient` inside the function to avoid cycles and `webcompy/rpc/_contracts.py` has no top-level `webcompy_server` import; update docstring/API placement so the client-facing contract usage is the documented path; `ruff check` + `pyright` clean
- [ ] 5.2 Add typed contract usage to unit tests so pyright validates inference (result types including `batch` `tuple[R1, R2]` and `RpcStream[T]`/`RpcSubscription[E]` element types) as part of the CI type check

## 6. Test suite migration

- [ ] 6.1 Migrate `tests/test_rpc_registry.py`, `test_rpc_client.py`, `test_rpc_dispatcher.py`, `test_rpc_integration.py`, and `test_rpc_mount.py` to contract-based registration and calls (schema module fixture, bind, contract invocation with fakes)
- [ ] 6.2 Migrate `tests/test_rpc_ws_client.py`, `test_rpc_ws_dispatcher.py`, and `test_rpc_ws_ssr.py` to contract usage, keeping all wire-level assertions (frames, cursors, replay, resync, heartbeat, SSR no-op) unchanged
- [ ] 6.3 Migrate any streaming tests added by `feat-rpc-streaming` to `StreamingProcedure` contract usage while keeping the SSE/WS wire assertions

## 7. E2E

- [ ] 7.1 Update `e2e/core/my_app/app.py` (schema module + `bind` for a procedure, a streaming procedure, and a subscription) and `e2e/core/my_app/pages/rpc_ws.py` (contract-based calls, streams, and subscriptions); adapt streaming E2E pages added by `feat-rpc-streaming` to contract usage
- [ ] 7.2 Run the core E2E group via `scripts/run-e2e-tests.sh` and fix failures

## 8. Docs

- [ ] 8.1 Add `docs_app/documents/rpc_contracts.md` (contract classes, schema-module convention, bind validation, transports, SSR behavior, non-goals) and register it in `docs_app/docs_manifest.py` with the page stub under `docs_app/pages/document/`
- [ ] 8.2 Rewrite `docs_app/documents/rpc_websocket.md` (and `rpc.md` if present) to contract-based usage; remove module-function and string-name examples; update the see-also links
- [ ] 8.3 Update `scripts/check-doc-spec-refs.py`: extend `DOC_FILES` to also scan `docs_app/documents/*.md` (or add a second scan), then add retired API names with qualified patterns so the new typed `batch(*RpcCall)` is not blocklisted and `register_type_handler` is not flagged: `r"\\bapp\\.rpc\\.register\\b"`, `r"\\bapp\\.rpc\\.procedure\\b"`, `r"\\brpc\\.call\\b"`, `r"\\brpc\\.notify\\b"`, `r"\\brpc\\.stream\\b"`, `r"\\bregister_subscription\\b"`, `r"\\bRpcWsClient\\.call\\b"`, `r"\\bRpcWsClient\\.subscribe\\b"` (bare `register` and bare `rpc.batch` SHALL NOT be used — the latter would flag the new typed `batch`); remove old stringly-typed `batch([("method", ...)])` examples from docs in `8.2` so the scan passes; run the script until it passes

## 9. Review knowledge sync

- [ ] 9.1 Update `AGENTS.md`: File → Spec Mapping (add `rpc-contracts`, `webcompy/rpc/_contracts.py`), Framework Invariants (add the RPC Contract Binding invariant), and the Current Specs list; update `.opencode/skills/webcompy-review/SKILL.md` Critical Framework Invariants accordingly
- [ ] 9.2 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes

## 10. Verification

- [ ] 10.1 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, and `uv run python -m pytest tests/ --tb=short`; fix all failures
- [ ] 10.2 Run `openspec validate feat-rpc-contracts --strict` and `openspec validate --specs`; resolve all findings
