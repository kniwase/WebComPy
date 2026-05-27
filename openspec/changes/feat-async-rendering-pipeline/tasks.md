## 1. Convert ElementAbstract._render() to async

- [ ] 1.1 Change `ElementAbstract._render()` from `def _render(self):` to `async def _render(self):` in `webcompy/elements/types/_abstract.py`
- [ ] 1.2 Update `ElementAbstract._render()` body to remain `self._mount_node()` (sync, no await needed since `_mount_node()` stays sync)

## 2. Convert ElementWithChildren._render() to async with asyncio.gather()

- [ ] 2.1 Change `ElementWithChildren._render()` to `async def _render(self):` in `webcompy/elements/types/_base.py`
- [ ] 2.2 Replace sequential `for child in self._children: child._render()` with `await asyncio.gather(*[child._render() for child in self._children])`
- [ ] 2.3 Add `import asyncio` to `_base.py`
- [ ] 2.4 Update `ElementWithChildren._hydrate_node()` — change the `for child in self._children: child._hydrate_node()` loop to a sync loop (hydration is not async in this change)
- [ ] 2.5 Document that `_hydrate_node()` callers may encounter children with no matching prerendered nodes. These un-hydrated children need async `_render()` scheduling, which is handled by downstream changes: `feat-client-only-component` (ClientOnly._hydrate_node() schedules `asyncio.ensure_future(self._render())`) and `feat-suspense-component` (Suspense._hydrate_node() schedules async resolution). The foundational async-rendering-pipeline change does NOT modify `_hydrate_node()` to schedule async rendering — it keeps hydration synchronous.

## 3. Convert DynamicElement._render() to async

- [ ] 3.1 Change `DynamicElement._render()` to `async def _render(self):` in `webcompy/elements/types/_dynamic.py`
- [ ] 3.2 Update the `for child in self._children:` loop to await each `child._render()` call — change `child._render()` to `await child._render()` for unmounted children
- [ ] 3.3 Add `import asyncio` if needed for gather patterns

## 4. Convert RepeatElement._render() and _refresh() to async

- [ ] 4.1 Change `RepeatElement._render()` to `async def _render(self):` in `webcompy/elements/types/_repeat.py`
- [ ] 4.2 Change `RepeatElement._refresh()` to `async def _refresh(self, *args):`
- [ ] 4.3 In `_refresh()`, update child `_render()` calls to `await child._render()` in the non-keyed branch
- [ ] 4.4 In `_refresh()`, update the `_reconcile_children()` method — child `_render()` calls in the keyed branch to `await child._render()`
- [ ] 4.5 Update signal callback registration in `_render()`: wrap async `_refresh` with `_make_signal_callback()` utility
- [ ] 4.6 Add `_make_signal_callback` import from `webcompy.aio`

## 5. Convert SwitchElement._render() and _refresh() to async

- [ ] 5.1 Change `SwitchElement._render()` to `async def _render(self):` in `webcompy/elements/types/_switch.py`
- [ ] 5.2 Change `SwitchElement._refresh()` to `async def _refresh(self, *args):`
- [ ] 5.3 In `_render()`, update `child._render()` calls to `await child._render()`
- [ ] 5.4 In `_refresh()`, update `child._render()` calls to `await child._render()`
- [ ] 5.5 Update the deferred `on_after_rendering` callback scheduling — async callbacks wrapped with `aio_run()`
- [ ] 5.6 Update signal callback registration in `_render()` and `_on_set_parent()`: wrap async `_refresh` with `_make_signal_callback()`

## 6. Convert Component._render() to async with async lifecycle hooks

- [ ] 6.1 Change `Component._render()` to `async def _render(self):` in `webcompy/components/_component.py`
- [ ] 6.2 Add `inspect.iscoroutinefunction` import
- [ ] 6.3 Update `on_before_rendering` invocation: detect async via `iscoroutinefunction()` and `await` if async
- [ ] 6.4 Update `on_after_rendering` invocation: detect async via `iscoroutinefunction()` and `await` if async (both direct and deferred paths)
- [ ] 6.5 Update the deferred callback mechanism: when `on_after_rendering` is async and deferred, schedule it via `aio_run()` in `end_defer_after_rendering()`
- [ ] 6.6 Add `import asyncio` to `_component.py`
- [ ] 6.7 **Interface contract**: `async def _render(self)` must have a clear extension point at the top of the method body for `feat/async-component-setup` to insert `_pending_async_template` resolution. Reserve a comment placeholder: `# [async-component-setup] Resolve pending async template if present`

## 7. Update ComponentProperty and Context types for async hooks

- [ ] 7.1 Update `ComponentProperty` TypedDict in `webcompy/components/_libs.py`: change `on_before_rendering`, `on_after_rendering`, `on_before_destroy` type hints to `Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]`
- [ ] 7.2 Update `Context.__on_before_rendering`, `Context.__on_after_rendering`, `Context.__on_before_destroy` type hints to accept async callables
- [ ] 7.3 Update `Context.on_before_rendering()`, `Context.on_after_rendering()`, `Context.on_before_destroy()` method signatures to accept `Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]`
- [ ] 7.4 Update standalone `@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy` decorators in `webcompy/components/_hooks.py` to accept async callables (type hint only, no behavior change)
- [ ] 7.5 Add `Coroutine` import to `_libs.py`

## 8. Convert AppDocumentRoot._render() to async

- [ ] 8.1 Change `AppDocumentRoot._render()` to `async def _render(self):` in `webcompy/app/_root_component.py`
- [ ] 8.2 Update `on_before_rendering` and `on_after_rendering` calls to use `iscoroutinefunction()` detection and `await` when async
- [ ] 8.3 Replace `for child in self._children: child._render()` with `await asyncio.gather(*[child._render() for child in self._children])`
- [ ] 8.4 Update `AppDocumentRoot.render` property — it currently returns `self._render`, which is now an async method. Ensure the property returns the coroutine function correctly for `app.run()` to schedule it
- [ ] 8.5 Add `import asyncio` and `from inspect import iscoroutinefunction` to `_root_component.py`

## 9. Update app.run() to schedule async render

- [ ] 9.1 In `webcompy/app/_app.py`, update `WebComPyApp.run()`: replace `self._root.render()` with `asyncio.ensure_future(self._root._render())`
- [ ] 9.2 Add `import asyncio` to `_app.py`

## 10. Convert generate_html() and _HtmlElement.render_html() to async

- [ ] 10.1 Change `_HtmlElement.render_html()` to `async def render_html(self):` in `webcompy/cli/_html.py`
- [ ] 10.2 Update `self._render()` call to `await self._render()` in `render_html()`
- [ ] 10.3 Change `generate_html()` to `async def generate_html(...) -> str:` in `webcompy/cli/_html.py`
- [ ] 10.4 Update `html_generator()` calls in `generate_html()` to `await html_generator()` — but since `html_generator` is a `functools.partial` wrapping `generate_html`, this needs careful handling. Actually, `html_generator` in `_generate.py` and `_server.py` wraps `generate_html` via `functools.partial`. Update these call sites.
- [ ] 10.5 Add `import asyncio` to `_html.py`

## 11. Update generate_static_site() for async generate_html()

- [ ] 11.1 Change `generate_static_site()` to `async def generate_static_site(app=None):` in `webcompy/cli/_generate.py`
- [ ] 11.2 Update all `html_generator()` calls to `await html_generator()` (since `html_generator` wraps `generate_html` which is now async)
- [ ] 11.3 Update the CLI entry point: wrap `generate_static_site()` call in `asyncio.run()`
- [ ] 11.4 Add `import asyncio` to `_generate.py`

## 12. Update dev server for async generate_html()

- [ ] 12.1 In `webcompy/cli/_server.py`, update `send_html` handler to `await html_generator()` since `generate_html` is now async
- [ ] 12.2 Update the `html_generator = partial(generate_html, ...)` — `generate_html` is now async, so `html_generator()` returns a coroutine. Call sites must `await html_generator()`
- [ ] 12.3 Verify the Starlette handler is already `async def` (it is — confirmed in the source)

## 13. Add _make_signal_callback() utility

- [ ] 13.1 Add `_make_signal_callback()` function to `webcompy/aio/_aio.py`:
  ```python
  def _make_signal_callback(callback):
      if iscoroutinefunction(callback):
          def wrapper(*args, **kwargs):
              aio_run(callback(*args, **kwargs))
          return wrapper
      return callback
  ```
- [ ] 13.2 Add `from inspect import iscoroutinefunction` to `_aio.py`
- [ ] 13.3 Export `_make_signal_callback` from `webcompy/aio/__init__.py`

## 14. Update ElementBase and TextElement _render() compatibility

- [ ] 14.1 Verify `ElementBase` (which extends `ElementWithChildren`) doesn't override `_render()` — if it does, update the override to `async def`
- [ ] 14.2 Verify `TextElement` and other element subclasses handle the async `_render()` signature correctly

## 15. Update tests for async rendering

- [ ] 15.1 Update any unit tests that directly call `element._render()` to use `await element._render()` with `asyncio.run()` or `pytest-asyncio`
- [ ] 15.2 Update any unit tests that call `generate_html()` to use `await generate_html()`
- [ ] 15.3 Verify the `TestRenderer` in `webcompy/testing/` handles async `_render()` — update `TestRenderer.render()` to `async def render()` and await the component's `_render()`
- [ ] 15.4 Update `create_test_asgi_app()` to await `generate_html()`

## 16. Verification

- [ ] 16.1 Run lint: `uv run ruff check .`
- [ ] 16.2 Run format: `uv run ruff format .`
- [ ] 16.3 Run type check: `uv run pyright`
- [ ] 16.4 Run unit tests: `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs`
- [ ] 16.5 Run SSG: `uv run python -m webcompy generate --config docs_app.webcompy_config` (update CLI entry to use `asyncio.run()`)
- [ ] 16.6 Run E2E tests: `scripts/run-e2e-tests.sh bootstrap-static`