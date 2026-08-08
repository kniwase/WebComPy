# Tasks: feat-json-rpc

## 1. Dispatcher core

- [ ] 1.1 Implement the JSON-RPC 2.0 dispatcher endpoint (packages/webcompy-server/src/webcompy_server/rpc/): envelope validation, single/batch, notifications, standard error codes
- [ ] 1.2 Implement the procedure registry with decorator and explicit registration; reject untyped/`**kwargs` signatures at registration time; derive param/result schemas from annotations
- [ ] 1.3 Implement invocation pipeline: strict `from_json` param decoding, sync/async procedure support, exception → `-32603` with generic client message and server-side logging

## 2. Typed wire and security

- [ ] 2.1 Support the `meta` extension member on requests and responses (typed-response wire format); result encoding via `encode_with_meta`
- [ ] 2.2 Implement the allowlist type registry (reusing `register_type_handler` concepts, scoped per registry) and enforce closed-set decoding; no class resolution from client-controlled names
- [ ] 2.3 Map validation failures to `-32602`, unknown methods to `-32601`, parse/envelope errors to `-32700`/`-32600`

## 3. Mount and client

- [ ] 3.1 Mount the dispatcher at `/_webcompy-rpc` as a framework-internal route via the `feat-asgi-mount` route-insertion point when procedures are registered (bypassing user-mount collision validation, per the `cli` delta); support custom mount path; register the reserved prefix
- [ ] 3.2 Implement the browser/SSR client (`rpc.call(method, params, result_type=T)`) over FetchPort with `RpcError` mapping
- [ ] 3.3 Verify SSR/SSG in-process dispatch and hydration bake; verify `transfer=False` opt-out

## 4. Tests

- [ ] 4.1 Protocol conformance tests: single/batch/notification, all standard error codes, generic JSON-RPC client interop without meta, including the all-notification batch (no response body at all) and empty batch array (`-32600`) edge cases
- [ ] 4.2 Typed decoding tests: dataclass params/results, meta restoration, strict rejection of extra keys, unregistered tag rejection (no class resolution)
- [ ] 4.3 Registration tests: decorator, duplicate names, untyped rejection
- [ ] 4.4 Integration tests: component RPC during SSR with bake; browser path; error propagation to `RpcError`
- [ ] 4.5 Security test: crafted meta referencing arbitrary module-qualified class names is rejected without import attempts

## 5. Docs and verification

- [ ] 5.1 Docs: defining procedures with shared dataclasses, calling from components, security model (allowlist), batch/notification usage (per `doc-spec-references`: docs reference the owning specs as source of truth rather than transcribing requirement prose)
- [ ] 5.2 `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short` all pass

## 6. Spec reference sync

- [ ] 6.1 Update AGENTS.md: add `json-rpc` to the Current Specs list; add File→Spec Mapping entries for `webcompy_server/rpc/` (`json-rpc/spec.md`) and the browser client module, and update the `cli` rows for the reserved dispatcher endpoint
- [ ] 6.2 Check `.opencode/skills/webcompy-review/SKILL.md` for stale assumptions and sync invariant headings/spec references
- [ ] 6.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
