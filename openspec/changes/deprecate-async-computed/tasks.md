## 1. Remove AsyncComputed from codebase

- [ ] 1.1 Delete the `AsyncComputed` class from `webcompy/aio/_aio.py` (lines 84–120)
- [ ] 1.2 Remove `AsyncComputed` from `webcompy/aio/__init__.py` imports and `__all__`
- [ ] 1.3 Run `uv run ruff check .` and `uv run ruff format .`
- [ ] 1.4 Run `uv run pyright` and fix any type errors caused by the removal
- [ ] 1.5 Run `uv run python -m pytest tests/ --tb=short` and verify all tests pass

## 2. Update specifications

- [ ] 2.1 Update `openspec/specs/overview/spec.md`: replace the `AsyncComputed` mention in the async requirement scenario with `AsyncResult` / `useAsyncResult` language
- [ ] 2.2 Update `openspec/specs/async/spec.md`: ensure the spec reflects `AsyncResult` and `useAsyncResult` as the sole async state primitives (verify no `AsyncComputed` references remain)

## 3. Remove resolved known issues from config

- [ ] 3.1 Remove the two Async-related known issues from `openspec/config.yaml`:
  - `AsyncComputed.value is T | None — no way to distinguish "not yet resolved" from "resolved to None" without checking done flag`
  - `AsyncComputed._error sets _done = False on error, conflating error state with pending state`
- [ ] 3.2 If this leaves the `### Async` section empty, remove the entire section

## 4. Final verification

- [ ] 4.1 Run full lint + typecheck + test: `uv run ruff check . && uv run ruff format . && uv run pyright && uv run python -m pytest tests/ --tb=short`
- [ ] 4.2 Verify `openspec validate` passes with updated specs and config