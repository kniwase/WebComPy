## 1. Template expression evaluator (53 warnings)

- [x] 1.1 In `packages/webcompy/src/webcompy/template/_expression.py`, replace the `node_type = type(node)` intermediate-variable dispatch in `_eval_node` with direct `isinstance(node, ast.X)` checks for each branch (`ast.Name`, `ast.Constant`, `ast.Attribute`, `ast.Subscript`, `ast.Slice`, `ast.List`, `ast.Tuple`, `ast.Set`, `ast.Dict`, `ast.UnaryOp`, `ast.BinOp`, `ast.BoolOp`, `ast.Compare`, `ast.IfExp`, `ast.Call`)
- [x] 1.2 Remove the now-unused `node_type = type(node)` assignment and verify no other code in the module depends on the `node_type` local
- [x] 1.3 Run `uv run pyright packages/webcompy/src/webcompy/template/_expression.py` and confirm the 53 `reportAttributeAccessIssue` warnings are gone

## 2. Element tree base + Suspense + Component (5 warnings)

- [x] 2.1 In `packages/webcompy/src/webcompy/elements/types/_abstract.py`, declare `_children: list[ElementAbstract] = []  # noqa: RUF012` on `ElementAbstract` (after the existing `_callback_nodes` declaration, before `_parent`)
- [x] 2.2 In `packages/webcompy/src/webcompy/components/_component.py`, rename `__init_component` to `_init_component` (the definition at ~line 186 and the two internal call sites at ~lines 100 and 257)
- [x] 2.3 In `packages/webcompy/src/webcompy/elements/types/_suspense.py`, update the external call `component._Component__init_component(component._property)` at ~line 82 to `component._init_component(component._property)`
- [x] 2.4 Confirm the `hasattr(element, "_children")` guards in `_suspense.py` (`_collect_pending_coroutines` and `_hydrate_node`) now type-check without warning thanks to the base declaration; leave the runtime `hasattr`/`isinstance(element._children, (list, tuple))` guards intact for safety
- [x] 2.5 Run `uv run pyright` on `_abstract.py`, `_component.py`, and `_suspense.py` and confirm the 5 warnings are gone

## 3. Signal producer retyping (2 warnings)

- [x] 3.1 In `packages/webcompy/src/webcompy/signal/_base.py`, change the `CallbackConsumerNode._producer` field annotation from `SignalNode` to `SignalBase[Any]`
- [x] 3.2 In the same `__init__`, change the `producer` parameter type from `SignalNode` to `SignalBase[Any]`
- [x] 3.3 Verify `_CallbackMixin` does not redeclare `_producer` (confirmed during exploration) and that `producer_add_live_consumer` / `producer_update_value_version` still accept the retyped producer (they take `SignalNode`, of which `SignalBase` is a subclass)
- [x] 3.4 Run `uv run pyright packages/webcompy/src/webcompy/signal/_base.py` and confirm the 2 warnings are gone

## 4. CLI build config sentinel (4 warnings)

- [x] 4.1 In `packages/webcompy-cli/src/webcompy_cli/config/_build_config.py`, define a module-private `_Sentinel` class and type `_UNSET: _Sentinel = _Sentinel()`
- [x] 4.2 Retype `_explicit_wasm_serving` and `_explicit_runtime_serving` from `Literal["cdn", "local"] | object` to `Literal["cdn", "local"] | _Sentinel`
- [x] 4.3 Confirm the `isinstance(self._explicit_*, _Sentinel)` guards now narrow correctly (the `is _UNSET` identity check does not narrow `_Sentinel` away) and the assignments to `self.wasm_serving` / `self.runtime_serving` in `resolve_standalone` are warning-free
- [x] 4.4 Run `uv run pyright` on `_build_config.py` and confirm the 4 warnings are gone

## 5. RenderContext disposal Optional widening (3 warnings)

- [x] 5.1 In `packages/webcompy/src/webcompy/app/_render_context.py`, widen the `_root`, `_di_scope`, and `_component_store` attribute declarations to `... | None` so the `= None` assignments in `dispose()` are type-valid
- [x] 5.2 Add `assert` narrowing at read sites (properties, `dispose()`, `_register_ports` in `BrowserRenderContext` and `ServerRenderContext`, `_load_hydration_payload`) — pyright cannot infer that `_check_disposed()` raises, so the widened types require explicit narrowing
- [x] 5.3 Run `uv run pyright packages/webcompy/src/webcompy/app/_render_context.py` and confirm the 3 warnings are gone

## 6. Router TypedDict + SSG/Server dynamic attributes (3 warnings)

- [x] 6.1 In `packages/webcompy/src/webcompy/router/_pages.py`, add `_preload: Callable[[], None]` to the `RouterPage` TypedDict (the `total=False` portion) and add the `Callable` import
- [x] 6.2 In `packages/webcompy-cli/src/webcompy_cli/_generate.py`, change the SSG guard from `hasattr(page, "_preload")` to `"_preload" in page` with index access `page["_preload"]()` (pyright requires TypedDict item access via index, not attribute), and change `app_module.app = app` to `cast("Any", app_module).app = app` (ruff B010 rejects `setattr` with a constant name)
- [x] 6.3 In `packages/webcompy-cli/src/webcompy_cli/_server.py`, change `app_module.app = app` to `setattr(app_module, "app", app)`
- [x] 6.4 Run `uv run pyright` on `_pages.py`, `_generate.py`, and `_server.py` and confirm the 3 warnings are gone

## 7. Full verification

- [x] 7.1 Run `uv run ruff check . && uv run ruff format --check .` — expect both clean
- [x] 7.2 Run `uv run ruff format .` if any formatting drifted from the edits
- [x] 7.3 Run `uv run pyright` — expect `0 errors, 0 warnings`
- [x] 7.4 Run `uv run python -m pytest tests/ --tb=short` — expect all unit tests green
- [x] 7.5 Run `scripts/run-e2e-tests.sh` (or at minimum the `components` and `docs-home` groups) to confirm the Suspense SSR resolution path, the SSG preload path, and hydration are unaffected
- [x] 7.6 Confirm `uv run python -m webcompy generate` still succeeds on `docs_app` (the SSG path touched by the `_preload` / `setattr` changes)
