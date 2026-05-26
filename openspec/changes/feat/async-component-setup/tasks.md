## 1. Update types and decorator

- [ ] 1.1 In `webcompy/components/_libs.py`, update `ComponentProperty["template"]` type from `ElementChildren` to `ElementChildren | None`
- [ ] 1.2 In `webcompy/components/_component.py`, update `FuncComponentDef` type alias to accept `Callable[[Context[Any]], Coroutine[Any, Any, ElementChildren]]` in addition to the sync variant
- [ ] 1.3 In `webcompy/components/_generator.py`, update `define_component` parameter type to accept async callables (`Callable[[...], ElementChildren] | Callable[[...], Coroutine[Any, Any, ElementChildren]]`)
- [ ] 1.4 In `webcompy/components/_generator.py`, update `FuncComponentDef` type alias to match the broader type from `_component.py`

## 2. Modify Component.__init__ and __setup

- [ ] 2.1 In `webcompy/components/_component.py`, add `self._pending_async_template: Coroutine[Any, Any, ElementChildren] | None = None` to `Component.__init__()`
- [ ] 2.2 Add `from collections.abc import Coroutine` and `from inspect import iscoroutinefunction` imports to `_component.py`
- [ ] 2.3 In `Component.__setup__()`, before calling `component_def(context)`, check `iscoroutinefunction(component_def)`:
  - If async: call `component_def(context)` to get the coroutine, store in `self._pending_async_template`, set `template = None`
  - If sync: call `component_def(context)` and use the result as `template` (unchanged)
- [ ] 2.4 In `Component.__init__()`, guard `self.__init_component(property)` — only call if `self._pending_async_template is None`

## 3. Modify Component._render

- [ ] 3.1 At the start of `Component._render()`, add the two-phase init resolution block:
  ```python
  if self._pending_async_template is not None:
      template = await self._pending_async_template
      self._pending_async_template = None
      property = self._property
      property["template"] = template
      self.__init_component(property)
  ```
- [ ] 3.2 Verify that after this block, the existing lifecycle hook and `super()._render()` logic runs as normal

## 4. Verification

- [ ] 4.1 Run lint: `uv run ruff check .`
- [ ] 4.2 Run format: `uv run ruff format .`
- [ ] 4.3 Run type check: `uv run pyright`
- [ ] 4.4 Run unit tests: `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs`
- [ ] 4.5 Run SSG: `uv run python -m webcompy generate --app docs_app.bootstrap:app`
- [ ] 4.6 Run E2E tests: `scripts/run-e2e-tests.sh bootstrap-static`
