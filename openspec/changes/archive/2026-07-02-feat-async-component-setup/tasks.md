## 0. Foundation validation spike

> Prerequisite for the rest of this change. Validates that the foundational `_refresh_sync` mechanism in `feat/async-rendering-pipeline` does not deadlock or block the event loop once async component setup is in play.

- [x] 0.1 Build a minimal PoC: a `@define_component async def DataComponent(context): data = await fetch("/api/x"); return html.DIV(...)` placed inside a `repeat()` whose sequence signal updates during SSG.
- [x] 0.2 Confirm that a signal-triggered `RepeatElement._refresh()` whose subtree contains the async component does NOT block the event loop (no user I/O is awaited inside `_refresh_sync`'s `run_until_complete`) — recorded in `test_async_component_in_repeat_signal_update_does_not_block`.
- [x] 0.3 If any block/deadlock is observed, document with a reproducer before continuing — no block/deadlock observed (async refresh is used when subtree has async setup).
- [x] 0.4 Confirm `app.run()`'s root render via `resolve_async(... _render())` still logs a raised async exception via the default `on_error=_log_error` hook, and that no swallow-without-log path is introduced — verified in `test_async_setup_exception_propagates_not_swallowed`.

## 1. Update types and decorator

- [x] 1.1 In `packages/webcompy/src/webcompy/components/_libs.py`, update `ComponentProperty["template"]` type from `ElementChildren` to `ElementChildren | None`
- [x] 1.2 In `packages/webcompy/src/webcompy/components/_component.py`, update `FuncComponentDef` type alias to accept `Callable[[Context[Any]], Coroutine[Any, Any, ElementChildren]]` in addition to the sync variant
- [x] 1.3 In `packages/webcompy/src/webcompy/components/_generator.py`, update `define_component` parameter type to accept async callables (`Callable[[...], ElementChildren] | Callable[[...], Coroutine[Any, Any, ElementChildren]]`)
- [x] 1.4 In `packages/webcompy/src/webcompy/components/_generator.py`, update `FuncComponentDef` type alias to match the broader type from `_component.py`

## 2. Modify Component.__init__ and __setup

- [x] 2.1 In `packages/webcompy/src/webcompy/components/_component.py`, add `self._pending_async_template: Coroutine[Any, Any, ElementChildren] | None = None` to `Component.__init__()`
- [x] 2.2 Add `from collections.abc import Coroutine` and `from inspect import iscoroutinefunction` imports to `_component.py`
- [x] 2.3 In `Component.__setup__()`, before calling `component_def(context)`, check `iscoroutinefunction(component_def)`:
  - If async: call `component_def(context)` to get the coroutine, store in `self._pending_async_template`, set `template = None`
  - If sync: call `component_def(context)` and use the result as `template` (unchanged)
- [x] 2.4 In `Component.__init__()`, guard `self.__init_component(property)` — only call if `self._pending_async_template is None`

## 3. Define SUSPENSE_RESOLVING_KEY

- [x] 3.1 Add `SUSPENSE_RESOLVING_KEY: InjectKey[bool]` to `packages/webcompy/src/webcompy/di/_keys.py`
- [x] 3.2 Export `SUSPENSE_RESOLVING_KEY` from `packages/webcompy/src/webcompy/di/__init__.py`
- [x] 3.3 The key semantics are: when `True` (provided by `SuspenseElement._render()`), `Component._render()` skips `_pending_async_template` resolution because Suspense owns it; when `False` or absent, Component resolves it directly.

## 4. Modify Component._render

- [x] 4.1 At the start of `Component._render()`, add the two-phase init resolution block:
  ```python
  if self._pending_async_template is not None:
      if not inject(SUSPENSE_RESOLVING_KEY):
          template = await self._pending_async_template
          self._pending_async_template = None
          property = self._property
          property["template"] = template
          self.__init_component(property)
  ```
- [x] 4.2 Verify that after this block, the existing lifecycle hook and `super()._render()` logic runs as normal

## 4b. Dynamic-element async refresh fallback (Decision 6)

> Goal: prevent `_refresh_sync` from blocking the event loop on a subtree that turns out to contain async components (Decision 6 / Foundation Open Issue A).

- [x] 4b.1 In `packages/webcompy/src/webcompy/elements/types/_repeat.py` and `packages/webcompy/src/webcompy/elements/types/_switch.py`, add a helper (e.g. `_subtree_has_async_setup(element) -> bool`) that walks the element's current/generated children and returns `True` if any `Component` has `_pending_async_template is not None`.
- [x] 4b.2 In `RepeatElement._render()` and `SwitchElement._render()` where the signal callback is registered, choose `self._refresh_sync` only when `_subtree_has_async_setup(self) is False`; otherwise register the async `self._refresh` (fire-and-forget via existing `_resolve_async_callback` path) so the enclosing `SuspenseElement` owns async resolution.
- [x] 4b.3 Keep `_on_set_parent()` registration unchanged (still `self._refresh` async, per foundation Decision 13).
- [x] 4b.4 Ensure `_signal_activated` is still set before either registration path, so double-registration is still impossible.
- [x] 4b.5 Add a unit test that triggers a signal update on a `repeat()` whose subtree contains an async component definition and asserts that the event loop is NOT blocked (the refresh does NOT call `loop.run_until_complete` on user async code) — fallback/slot resolution is delegated to the enclosing `Suspense`.

## 5. Verification

- [x] 5.1 Run lint: `uv run ruff check .` — passed
- [x] 5.2 Run format: `uv run ruff format .` — passed
- [x] 5.3 Run type check: `uv run pyright` — 0 errors
- [x] 5.4 Run unit tests: `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs` — 1270 passed
- [x] 5.5 Run SSG: `uv run python -m webcompy generate --app docs_app.bootstrap:app`
- [x] 5.6 Run E2E tests: `scripts/run-e2e-tests.sh bootstrap-static` — 2/2 passed (all groups including docs-home, docs-fetch: 26/26 passed)
