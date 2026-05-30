## 1. Convert ElementAbstract._render() to async

- [x] 1.1 Change `ElementAbstract._render()` from `def _render(self):` to `async def _render(self):` in `webcompy/elements/types/_abstract.py`
- [x] 1.2 Update `ElementAbstract._render()` body to remain `self._mount_node()` (sync, no await needed since `_mount_node()` stays sync)

## 2. Convert ElementWithChildren._render() to async with asyncio.gather()

- [x] 2.1 Change `ElementWithChildren._render()` to `async def _render(self):` in `webcompy/elements/types/_base.py`
- [x] 2.2 Replace sequential `for child in self._children: child._render()` with `await asyncio.gather(*[child._render() for child in self._children])`
- [x] 2.3 Add `import asyncio` to `_base.py`
- [x] 2.4 Update `ElementWithChildren._hydrate_node()` — change the `for child in self._children: child._hydrate_node()` loop to a sync loop (hydration is not async in this change)
- [x] 2.5 Document that `_hydrate_node()` callers may encounter children with no matching prerendered nodes. These un-hydrated children need async `_render()` scheduling, which is handled by downstream changes: `feat-client-only-component` (ClientOnly._hydrate_node() schedules `asyncio.ensure_future(self._render())`) and `feat-suspense-component` (Suspense._hydrate_node() schedules async resolution). The foundational async-rendering-pipeline change does NOT modify `_hydrate_node()` to schedule async rendering — it keeps hydration synchronous.
- [x] 2.6 Implement PyScript ContextVar isolation for `asyncio.gather()` siblings: In the browser (Emscripten), Python ContextVar fallback uses shared module-level globals. Before starting each sibling coroutine in `asyncio.gather()`, the framework SHALL snapshot `_active_consumer` and `_active_di_scope` ContextVars and restore them at the start of each sibling task. This ensures sibling coroutines do not interfere with each other's signal dependency tracking or DI scope resolution. Wrap each child coroutine in a helper that (a) snapshots current ContextVar values, (b) restores them at task entry, and (c) runs the original child coroutine. The helper SHALL be applied in `ElementWithChildren._render()` and `AppDocumentRoot._render()` wherever `asyncio.gather()` is used for sibling rendering.

## 3. Convert DynamicElement._render() to async

- [x] 3.1 Change `DynamicElement._render()` to `async def _render(self):` in `webcompy/elements/types/_dynamic.py`
- [x] 3.2 Update the `for child in self._children:` loop to await each `child._render()` call — change `child._render()` to `await child._render()` for unmounted children
- [x] 3.3 Add `import asyncio` if needed for gather patterns

## 4. Convert RepeatElement._render() and _refresh() to async

- [x] 4.1 Change `RepeatElement._render()` to `async def _render(self):` in `webcompy/elements/types/_repeat.py`
- [x] 4.2 Change `RepeatElement._refresh()` to `async def _refresh(self, *args):`
- [x] 4.3 In `_refresh()`, update child `_render()` calls to `await child._render()` in the non-keyed branch
- [x] 4.4 In `_refresh()`, update the `_reconcile_children()` method — child `_render()` calls in the keyed branch to `await child._render()`
- [x] 4.5 Update signal callback registration in `_render()`: wrap async `_refresh` with `_make_signal_callback()` utility
- [x] 4.6 Add `_make_signal_callback` import from `webcompy.aio`

## 5. Convert SwitchElement._render() and _refresh() to async

- [x] 5.1 Change `SwitchElement._render()` to `async def _render(self):` in `webcompy/elements/types/_switch.py`
- [x] 5.2 Change `SwitchElement._refresh()` to `async def _refresh(self, *args):`
- [x] 5.3 In `_render()`, update `child._render()` calls to `await child._render()`
- [x] 5.4 In `_refresh()`, update `child._render()` calls to `await child._render()`
- [x] 5.5 Update the deferred `on_after_rendering` callback scheduling — async callbacks wrapped with `aio_run()`
- [x] 5.6 Update signal callback registration in `_render()` and `_on_set_parent()`: wrap async `_refresh` with `_make_signal_callback()`

## 6. Convert Component._render() to async with async lifecycle hooks

- [x] 6.1 Change `Component._render()` to `async def _render(self):` in `webcompy/components/_component.py`
- [x] 6.2 Add `inspect.iscoroutinefunction` import
- [x] 6.3 Update `on_before_rendering` invocation: detect async via `iscoroutinefunction()` and `await` if async
- [x] 6.4 Update `on_after_rendering` invocation: detect async via `iscoroutinefunction()` and `await` if async (both direct and deferred paths)
- [x] 6.5 Update the deferred callback mechanism: when `on_after_rendering` is async and deferred, schedule it via `aio_run()` in `end_defer_after_rendering()`
- [x] 6.6 Add `import asyncio` to `_component.py`
- [x] 6.7 **Interface contract**: `async def _render(self)` must have a clear extension point at the top of the method body for `feat/async-component-setup` to insert `_pending_async_template` resolution. Reserve a comment placeholder: `# [async-component-setup] Resolve pending async template if present`

## 7. Update ComponentProperty and Context types for async hooks

- [x] 7.1 Update `ComponentProperty` TypedDict in `webcompy/components/_libs.py`: change `on_before_rendering`, `on_after_rendering`, `on_before_destroy` type hints to `Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]`
- [x] 7.2 Update `Context.__on_before_rendering`, `Context.__on_after_rendering`, `Context.__on_before_destroy` type hints to accept async callables
- [x] 7.3 Update `Context.on_before_rendering()`, `Context.on_after_rendering()`, `Context.on_before_destroy()` method signatures to accept `Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]`
- [x] 7.4 Update standalone `@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy` decorators in `webcompy/components/_hooks.py` to accept async callables (type hint only, no behavior change)
- [x] 7.5 Add `Coroutine` import to `_libs.py`

## 8. Convert AppDocumentRoot._render() to async

- [x] 8.1 Change `AppDocumentRoot._render()` to `async def _render(self):` in `webcompy/app/_root_component.py`
- [x] 8.2 Update `on_before_rendering` and `on_after_rendering` calls to use `iscoroutinefunction()` detection and `await` when async
- [x] 8.3 Replace `for child in self._children: child._render()` with `await asyncio.gather(*[child._render() for child in self._children])`
- [x] 8.4 Update `AppDocumentRoot.render` property — it currently returns `self._render`, which is now an async method. Ensure the property returns the coroutine function correctly for `app.run()` to schedule it
- [x] 8.5 Add `import asyncio` and `from inspect import iscoroutinefunction` to `_root_component.py`

## 9. Update app.run() to schedule async render

- [x] 9.1 In `webcompy/app/_app.py`, update `WebComPyApp.run()`: replace `self._root.render()` with `asyncio.ensure_future(self._root._render())`
- [x] 9.2 Add `import asyncio` to `_app.py`

## 10. Convert generate_html() and _HtmlElement.render_html() to async

- [x] 10.1 Change `_HtmlElement.render_html()` to `async def render_html(self):` in `webcompy/cli/_html.py`
- [x] 10.2 Update `self._render()` call to `await self._render()` in `render_html()`
- [x] 10.3 Change `generate_html()` to `async def generate_html(...) -> str:` in `webcompy/cli/_html.py`
- [x] 10.4 Update `html_generator()` calls in `generate_html()` to `await html_generator()` — but since `html_generator` is a `functools.partial` wrapping `generate_html`, this needs careful handling. Actually, `html_generator` in `_generate.py` and `_server.py` wraps `generate_html` via `functools.partial`. Update these call sites.
- [x] 10.5 Add `import asyncio` to `_html.py`

## 11. Update generate_static_site() for async generate_html() — WILL BE SUPERSEDED BY feat-ssg-via-ssr

- [x] 11.1 Change `generate_static_site()` to `async def generate_static_site(app=None):` in `webcompy/cli/_generate.py`
- [x] 11.2 Update all `html_generator()` calls to `await html_generator()` (since `html_generator` wraps `generate_html` which is now async)
- [x] 11.3 Update the CLI entry point: wrap `generate_static_site()` call in `asyncio.run()`
- [x] 11.4 Add `import asyncio` to `_generate.py`

## 12. Update dev server for async generate_html() — WILL BE SUPERSEDED BY feat-ssg-via-ssr

- [x] 12.1 In `webcompy/cli/_server.py`, update `send_html` handler to `await html_generator()` since `generate_html` is now async
- [x] 12.2 Update the `html_generator = partial(generate_html, ...)` — `generate_html` is now async, so `html_generator()` returns a coroutine. Call sites must `await html_generator()`
- [x] 12.3 Verify the Starlette handler is already `async def` (it is — confirmed in the source)

## 13. Add _make_signal_callback() utility

- [x] 13.1 Add `_make_signal_callback()` function to `webcompy/aio/_aio.py`
- [x] 13.2 Add `from inspect import iscoroutinefunction` to `_aio.py`
- [x] 13.3 Export `_make_signal_callback` from `webcompy/aio/__init__.py`

## 14. Update ElementBase and TextElement _render() compatibility

- [x] 14.1 Verify `ElementBase` (which extends `ElementWithChildren`) doesn't override `_render()` — if it does, update the override to `async def`
- [x] 14.2 Verify `TextElement` and other element subclasses handle the async `_render()` signature correctly

## 15. Update tests for async rendering

- [ ] 15.1 Install pytest-asyncio: Add to dev dependencies in pyproject.toml and run `uv sync --group dev`
- [ ] 15.2 Configure pytest-asyncio: Add `asyncio_mode = "auto"` to `[tool.pytest.ini_options]` in pyproject.toml
- [ ] 15.3 Create `run_sync()` helper in `webcompy/aio/_utils.py` (or similar) for test utilities that need to call async code from sync context without `asyncio.run()`
- [ ] 15.4 Update `TestRenderer.render()` in `webcompy/testing/_renderer.py`: Convert to `async def render()` or use `run_sync()` wrapper. Ensure it works with pytest-asyncio's event loop.
- [ ] 15.5 Update `render_app_html_sync()` in `webcompy/testing/_asgi.py`: Use `run_sync()` instead of `asyncio.run()`
- [ ] 15.6 Update `tests/test_elements.py`: Convert test functions to `async def`, replace `asyncio.run(element._render())` with `await element._render()`
- [ ] 15.7 Update `tests/test_html_generation.py`: Convert to async tests, replace `asyncio.run(generate_html(...))` with `await generate_html(...)`
- [ ] 15.8 Update `tests/test_keyed_repeat.py`: Convert to async tests, replace `asyncio.run(rep._refresh())` with `await rep._refresh()`
- [ ] 15.9 Update `tests/test_nested_dynamic.py`: Convert to async tests
- [ ] 15.10 Update `tests/test_plugin_script.py`: Convert to async tests
- [ ] 15.11 Update `tests/test_plugin_system.py`: Convert to async tests
- [ ] 15.12 Update `tests/test_prerender_hidden.py`: Convert to async tests
- [ ] 15.13 Update `tests/test_preserve_children.py`: Convert to async tests
- [ ] 15.14 Update `tests/test_request_isolation.py`: Convert to async tests
- [ ] 15.15 Update `tests/test_runtime_local_integration.py`: Convert to async tests
- [ ] 15.16 Update `tests/test_scoped_css.py`: Convert to async tests
- [ ] 15.17 Update `tests/test_switch.py`: Convert to async tests
- [ ] 15.18 Update `tests/test_switch_patch.py`: Convert to async tests
- [ ] 15.19 Update `tests/test_unified_render_path.py`: Convert to async tests
- [ ] 15.20 Update `tests/test_tier1_component.py`, `test_tier1_static.py`, `test_tier2_interactive.py`: Convert to async tests
- [ ] 15.21 Update `tests/test_async_result.py`: Convert to async tests
- [ ] 15.22 Update `tests/test_hooks.py`: Convert to async tests
- [ ] 15.23 Update `tests/test_server_rendering.py`: Convert to async tests
- [ ] 15.24 Verify all test files compile and pytest collection works: `uv run python -m pytest tests/ --collect-only`

## 16. Verification

- [ ] 16.1 Run lint: `uv run ruff check .`
- [ ] 16.2 Run format: `uv run ruff format .`
- [ ] 16.3 Run type check: `uv run pyright`
- [ ] 16.4 Run unit tests: `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs` (all tests must pass)
- [ ] 16.5 Run SSG: `uv run python -m webcompy generate --config docs_app.webcompy_config`
- [ ] 16.6 Run E2E tests: `scripts/run-e2e-tests.sh bootstrap-static`