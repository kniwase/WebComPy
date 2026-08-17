# Tasks: feat-typed-realtime

## 1. Allowlist registry

- [x] 1.1 Create the app-scoped realtime type registry in `packages/webcompy/src/webcompy/realtime/_typed.py` (inject-or-provide pattern mirroring the connection registry; qualified-name tags; closed builtin tag set)
- [x] 1.2 Implement `register_realtime_type_handler(cls, encoder, decoder)` with no-DI-scope warning + no-op fallback

## 2. Typed layer

- [x] 2.1 Implement send-side encoding: `encode_with_meta(instance, type_handlers=...)` + `merge_meta_into_body` → JSON text frame via the raw handle's `.send()`
- [x] 2.2 Implement receive-side decoding: JSON parse → split `__webcompy_transfer_meta__` → `from_json(T, payload, meta=meta, strict=strict)` with allowlist decoders; dataclass-only target validation with descriptive error
- [x] 2.3 Implement the typed handle wrapper (`AsyncIterator[T]` + `.send(T)` + `.last_error: Signal[Exception | None]`) delegating sharing/reconnect/state/lifecycle to the raw handle; skip-on-error with warning and `.last_error` set/reset semantics
- [x] 2.4 Wire the `message_type`/`strict` parameters into `use_websocket` (default `None` preserves raw behavior) and export `register_realtime_type_handler` from `webcompy/realtime/__init__.py` and `webcompy/__init__.py`

## 3. Unit tests (`tests/`, browserless, using FakeWebSocketPort)

- [x] 3.1 Typed iteration: valid frames yield dataclass instances; raw handle unchanged when `message_type=None`
- [x] 3.2 Typed send: frame is a single JSON object with the `__webcompy_transfer_meta__` member; metadata fields (datetime/UUID/Decimal/Enum) round-trip
- [x] 3.3 Skip-on-error: non-JSON frame skipped with `.last_error` set; schema-mismatch frame skipped; unknown type tag skipped without class resolution; next valid frame yields and resets `.last_error`; subscription and shared connection survive
- [x] 3.4 Strict default: extra/missing fields skipped; `strict=False` yields leniently
- [x] 3.5 Allowlist: registered custom type round-trips; unregistered tag skipped; registration outside a DI scope warns and is not global
- [x] 3.6 Non-dataclass `message_type` raises a descriptive error
- [x] 3.7 SSR: typed handle falls back like the raw handle; no transfer payload entries

## 4. E2E tests (`e2e/core/`)

- [x] 4.1 Extend the mounted test WebSocket endpoint (asgi-mount) with a typed echo that returns metadata-typed fields
- [x] 4.2 Add a Playwright test: typed dataclass round trip renders typed fields; a malformed frame from the server does not break subsequent messages; gate with `WEBCOMPY_RUN_E2E=1`

## 5. Docs (Markdown-driven, per docs-site-documents)

- [x] 5.1 Add `docs_app/documents/typed_realtime.md`: `message_type` usage, wire envelope, strictness, `.last_error` handling recipe, allowlist registration
- [x] 5.2 Register the page in `docs_app/docs_manifest.py` and add the `docs_app/pages/document/typed_realtime.py` stub

## 6. Review knowledge sync

- [ ] 6.1 Update `AGENTS.md`: File → Spec Mapping row for `webcompy/realtime/_typed.py`; Current Specs entry for `typed-realtime`
- [ ] 6.2 Update `.opencode/skills/webcompy-review/SKILL.md` file→spec mapping and Critical Framework Invariants if a new invariant is introduced
- [ ] 6.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes

## 7. Validation

- [ ] 7.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 7.2 `uv run pyright` passes
- [ ] 7.3 `uv run python -m pytest tests/ --tb=short -q` passes (full suite, no regressions)
- [ ] 7.4 `openspec validate feat-typed-realtime` passes
