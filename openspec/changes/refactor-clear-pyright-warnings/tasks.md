## 1. Template expression evaluator (53 warnings)

- [ ] 1.1 In `packages/webcompy/src/webcompy/template/_expression.py`, replace the `node_type = type(node)` intermediate-variable dispatch in `_eval_node` with direct `isinstance(node, ast.X)` checks for each branch (`ast.Name`, `ast.Constant`, `ast.Attribute`, `ast.Subscript`, `ast.Slice`, `ast.List`, `ast.Tuple`, `ast.Set`, `ast.Dict`, `ast.UnaryOp`, `ast.BinOp`, `ast.BoolOp`, `ast.Compare`, `ast.IfExp`, `ast.Call`)
- [ ] 1.2 Remove the now-unused `node_type = type(node)` assignment and verify no other code in the module depends on the `node_type` local
- [ ] 1.3 Run `uv run pyright packages/webcompy/src/webcompy/template/_expression.py` and confirm the 53 `reportAttributeAccessIssue` warnings are gone

## 2. Element tree base + Suspense + Component (5 warnings)

- [ ] 2.1 In `packages/webcompy/src/webcompy/elements/types/_abstract.py`, declare `_children: list[ElementAbstract] = []  # noqa: RUF012` on `ElementAbstract` (after the existing `_callback_nodes` declaration, before `_parent`)
- [ ] 2.2 In `packages/webcompy/src/webcompy/components/_component.py`, rename `__init_component` to `_init_component` (the definition at ~line 186 and the two internal call sites at ~lines 100 and 257)
- [ ] 2.3 In `packages/webcompy/src/webcompy/elements/types/_suspense.py`, update the external call `component._Component__init_component(component._property)` at ~line 82 to `component._init_component(component._property)`
- [ ] 2.4 Confirm the `hasattr(element, "_children")` guards in `_suspense.py` (`_collect_pending_coroutines` and `_hydrate_node`) now type-check without warning thanks to the base declaration; leave the runtime `hasattr`/`isinstance(element._children, (list, tuple))` guards intact for safety
- [ ] 2.5 Run `uv run pyright` on `_abstract.py`, `_component.py`, and `_suspense.py` and confirm the 5 warnings are gone

## 3. Signal producer retyping (2 warnings)

- [ ] 3.1 In `packages/webcompy/src/webcompy/signal/_base.py`, change the `CallbackConsumerNode._producer` field annotation from `SignalNode` to `SignalBase[Any]`
- [ ] 3.2 In the same `__init__`, change the `producer` parameter type from `SignalNode` to `SignalBase[Any]`
- [ ] 3.3 Verify `_CallbackMixin` does not redeclare `_producer` (confirmed during exploration) and that `producer_add_live_consumer` / `producer_update_value_version` still accept the retyped producer (they take `SignalNode`, of which `SignalBase` is a subclass)
- [ ] 3.4 Run `uv run pyright packages/webcompy/src/webcompy/signal/_base.py` and confirm the 2 warnings are gone

## 4. CLI build config sentinel (4 warnings)

- [ ] 4.1 In `packages/webcompy-cli/src/webcompy_cli/config/_build_config.py`, define a module-private `_Sentinel` class and type `_UNSET: _Sentinel = _Sentinel()`
- [ ] 4.2 Retype `_explicit_wasm_serving` and `_explicit_runtime_serving` from `Literal["cdn", "local"] | object` to `Literal["cdn", "local"] | _Sentinel`
- [ ] 4.3 Confirm the `self._explicit_* is _UNSET` checks now narrow correctly and the assignments to `self.wasm_serving` / `self.runtime_serving` in `resolve_standalone` are warning-free
- [ ] 4.4 Run `uv run pyright` on `_build_config.py` and confirm the 4 warnings are gone

## 5. RenderContext disposal Optional widening (3 warnings)

- [ ] 5.1 In `packages/webcompy/src/webcompy/app/_render_context.py`, widen the `_root`, `_di_scope`, and `_component_store` attribute declarations to `... | None` so the `= None` assignments in `dispose()` are type-valid
- [ ] 5.2 Confirm read sites for these attributes are already guarded by `_check_disposed()` (which raises after disposal), so no new `None`-handling is needed
- [ ] 5.3 Run `uv run pyright packages/webcompy/src/webcompy/app/_render_context.py` and confirm the 3 warnings are gone

## 6. Router TypedDict + SSG/Server dynamic attributes (3 warnings)

- [ ] 6.1 In `packages/webcompy/src/webcompy/router/_pages.py`, add `_preload: Callable[[], None]` to the `RouterPage` TypedDict (the `total=False` portion) and add the `Callable` import
- [ ] 6.2 In `packages/webcompy-cli/src/webcompy_cli/_generate.py`, change the SSG guard from `hasattr(page, "_preload")` to `"_preload" in page` so pyright narrows the TypedDict, and change `app_module.app = app` to `setattr(app_module, "app", app)`
- [ ] 6.3 In `packages/webcompy-cli/src/webcompy_cli/_server.py`, change `app_module.app = app` to `setattr(app_module, "app", app)`
- [ ] 6.4 Run `uv run pyright` on `_pages.py`, `_generate.py`, and `_server.py` and confirm the 3 warnings are gone

## 7. Full verification

- [ ] 7.1 Run `uv run ruff check . && uv run ruff format --check .` — expect both clean
- [ ] 7.2 Run `uv run ruff format .` if any formatting drifted from the edits
- [ ] 7.3 Run `uv run pyright` — expect `0 errors, 0 warnings`
- [ ] 7.4 Run `uv run python -m pytest tests/ --tb=short` — expect all unit tests green
- [ ] 7.5 Run `scripts/run-e2e-tests.sh` (or at minimum the `components` and `docs-home` groups) to confirm the Suspense SSR resolution path, the SSG preload path, and hydration are unaffected
- [ ] 7.6 Confirm `uv run python -m webcompy generate` still succeeds on `docs_app` (the SSG path touched by the `_preload` / `setattr` changes)
