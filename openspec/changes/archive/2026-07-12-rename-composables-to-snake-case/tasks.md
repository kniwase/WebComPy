## 1. Rename core composable functions

- [x] 1.1 Rename `useRouter()` to `use_router()` in `packages/webcompy/src/webcompy/router/_composables.py` and update its public re-exports.
- [x] 1.2 Rename `useAsync()` to `use_async()` in `packages/webcompy/src/webcompy/components/_hooks.py`.
- [x] 1.3 Remove the `useAsyncResult()` camelCase alias from `packages/webcompy/src/webcompy/components/_hooks.py`, keeping only `use_async_result()`.
- [x] 1.4 Update `packages/webcompy/src/webcompy/components/__init__.py` to export `use_async` and `use_async_result` only (no `useAsync`, no `useAsyncResult`).

## 2. Update framework internal usages

- [x] 2.1 Search and replace all `useRouter` → `use_router` in `packages/`.
- [x] 2.2 Search and replace all `useAsyncResult` → `use_async_result` in `packages/`.
- [x] 2.3 Search and replace all `useAsync` → `use_async` in `packages/`.
- [x] 2.4 Update `AGENTS.md` spec mapping and any other internal references to the new names.

## 3. Update tests

- [x] 3.1 Update `tests/test_hooks.py` to use `use_async_result` and `use_async`.
- [x] 3.2 Update any other test files referencing the old camelCase names.
- [x] 3.3 Run `uv run python -m pytest tests/ --tb=short` and fix failures.

## 4. Update E2E pages and demos

- [x] 4.1 Update `e2e/core/my_app/pages/async_nav.py` to use `use_async`.
- [x] 4.2 Search and replace old names across `e2e/` and `docs_app/`.
- [x] 4.3 Run the relevant E2E groups (at least `router`, `components`, `dynamic-control`) to verify.

## 5. Update CLI templates and project scaffolding

- [x] 5.1 Search and replace old names in `packages/webcompy-cli/src/webcompy_cli/template_data/`.
- [x] 5.2 Verify `webcompy generate` still produces valid output for `docs_app`.

## 6. Add naming convention guidance

- [x] 6.1 Add a naming convention section to `AGENTS.md` under Code Conventions: public Python functions/variables use `snake_case`, classes use `PascalCase`, constants use `UPPER_CASE`, and DOM/browser API wrappers may use `camelCase` only when mirroring standard web API names.
- [x] 6.2 Note that WebComPy composables use `use_verb` / `use_noun` snake_case (e.g., `use_state`, `use_router`, `use_async`).

## 7. Bonus scope: address AI review items from PR #198

- [x] 7.1 Restore the lost type annotation on `navigation._open_states` in `docs_app/components/navigation.py`.
- [x] 7.2 Restore the named keyword parameter for `FizzbuzzList` in `packages/webcompy-cli/src/webcompy_cli/template_data/app/components/fizzbuzz.py` (changed from named to positional in PR #198).
- [x] 7.3 Verify both fixes with `uv run pyright` and relevant tests.

## 8. Update OpenSpec main specs

- [x] 8.1 Apply delta specs to `openspec/specs/composables/spec.md` (rename `useAsyncResult` → `use_async_result`, `useAsync` → `use_async`, `useRouter` → `use_router`).
- [x] 8.2 Apply delta specs to `openspec/specs/async/spec.md` (rename `useAsyncResult` → `use_async_result`).
- [x] 8.3 Apply delta specs to `openspec/specs/router/spec.md` (rename `useRouter` → `use_router`).
- [x] 8.4 Apply delta specs to `openspec/specs/overview/spec.md` (rename `useAsyncResult` → `use_async_result`).
- [x] 8.5 Update `.opencode/agents/ci-review.md` if the file→spec mapping or Critical Framework Invariants reference the old names.
- [x] 8.6 Run `openspec validate --specs` and `openspec validate --changes` and fix any issues.

## 9. Final verification and archive

- [x] 9.1 Run `uv run ruff check .` and `uv run ruff format .`.
- [x] 9.2 Run `uv run pyright`.
- [x] 9.3 Run `uv run python -m pytest tests/ --tb=short`.
- [x] 9.4 Run `scripts/run-e2e-tests.sh` (or the relevant subset) and verify no regressions.
- [ ] 9.5 Sync the delta specs to main specs and archive the `rename-composables-to-snake-case` change.
- [ ] 9.6 Commit with a clean history and open a PR.
