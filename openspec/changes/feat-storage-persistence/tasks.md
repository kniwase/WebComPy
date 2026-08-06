# Tasks

## 1. Implementation

- [x] 1.1 Create `packages/webcompy/src/webcompy/storage/__init__.py` and `_composable.py` per design D1–D4 (`use_local_storage`, `use_session_storage`, `_read`, `_write`, `_make`, overloads, `ENVIRONMENT` guard, `pyscript.context.window` access in browser branch only)
- [x] 1.2 Export both composables from `webcompy/__init__.py` (top-level) alongside the existing `use_*` exports
- [x] 1.3 Confirm no SSR transfer registration occurs for storage signals (design D5)

## 2. Tests

- [x] 2.1 Unit tests with a dict-backed fake storage (`tests/test_storage_composable.py`): round-trip, missing key → default (value and factory forms), stored `null` vs missing, corrupted JSON → warning + default, non-serializable value → warning + skip, setItem failure → swallowed
- [x] 2.2 Server-path test: no storage access in non-PyScript env (assert helper-level isolation and `Reactive(default)` return)
- [x] 2.3 Outside-setup call emits no warning
- [x] 2.4 Component integration via `webcompy_testing` TestRenderer: signal usable in template and updates trigger writes
- [x] 2.5 E2E: storage page in `e2e/core/my_app/pages/storage.py` + `e2e/core/test_storage.py` + register in `interaction` group (run-e2e-tests.sh and ci.yml)

## 3. Docs

- [x] 3.1 Deferred — docs_app has no composables page yet (`/documents` is Work In Progress); the storage docs section will be owned by the follow-up docs change (see proposal "Impact > Docs")
- [x] 3.2 Verify `uv run python -m webcompy generate` succeeds

## 4. Verification

- [ ] 4.1 `uv run ruff check .` and `uv run ruff format --check .`
- [ ] 4.2 `uv run pyright`
- [ ] 4.3 `uv run python -m pytest tests/ --tb=short` (all existing tests MUST pass)

## 5. Housekeeping (at archive time)

- [ ] 5.1 Update `AGENTS.md` File→Spec Mapping with `webcompy/storage/` → `composables/spec.md`
