## 1. Create ClientOnlyElement class

- [ ] 1.1 Create `webcompy/elements/types/_client_only.py` — implement `ClientOnlyElement(DynamicElement)` with `__init__(children: NodeGenerator, fallback: NodeGenerator | None)`, storing `ENVIRONMENT == "pyscript"` result in `self._is_client`. Override `_render()` to call `self._children_generator` only when `self._is_client` is True, otherwise call `self._fallback_generator` (or render empty placeholder). Override `_hydrate_node()` to render actual children in the browser, replacing SSR fallback. Override `_on_set_parent()` as no-op (no signal subscriptions needed).
- [ ] 1.2 Implement `_generate_fallback()` method — if `self._fallback_generator` is not None, call it and wrap result in `_create_child_element`. Otherwise, create an empty text node placeholder via `TextElement("")`.
- [ ] 1.3 Implement `_render()` — if `self._is_client`, generate children from `self._children_generator`; otherwise generate fallback. Set `self._children`, assign `_node_idx`, call `_render()` on each child, and call `_position_element_nodes()`.
- [ ] 1.4 Implement `_hydrate_node()` — if `self._is_client` (browser), generate children from `self._children_generator`, remove existing fallback placeholder nodes from the DOM, set `self._children`, assign `_node_idx`, and call `_render()` on each child. If not client (shouldn't normally happen during hydration), delegate to fallback rendering.
- [ ] 1.5 Implement `_generate_children()` method — call `self._children_generator`, wrap result in `_create_child_element`, return list. Follow the same pattern as `SwitchElement._generate_children()`.

**Estimated time**: ~1.5 hours

## 2. Add client_only() generator function and exports

- [ ] 2.1 Add `client_only()` function to `webcompy/elements/generators.py` — accepts `children: NodeGenerator` and optional `fallback: NodeGenerator | None = None`, returns `ClientOnlyElement(children, fallback)`.
- [ ] 2.2 Export `ClientOnlyElement` from `webcompy/elements/types/__init__.py`
- [ ] 2.3 Add `ClientOnly` as an alias for `ClientOnlyElement` in `webcompy/elements/__init__.py` and add to `__all__`. Add `client_only` to imports and `__all__`.

**Estimated time**: ~0.5 hours

## 3. Unit tests for ClientOnlyElement SSR behavior

- [ ] 3.1 Test: SSR rendering with fallback — create a `ClientOnly` element with fallback and children, render in server environment (`ENVIRONMENT != "pyscript"`), verify fallback content appears in output and children generator was never called.
- [ ] 3.2 Test: SSR rendering without fallback — create a `ClientOnly` element with only `children`, render in server environment, verify empty placeholder appears in output and children generator was never called.
- [ ] 3.3 Test: SSR with side-effect-generating children — create a `ClientOnly` with children that would create signals or call async fetches, render in server environment, verify none of the side effects occurred.

**Estimated time**: ~1.5 hours

## 4. Unit tests for ClientOnlyElement browser behavior

- [ ] 4.1 Test: Browser rendering with children — create a `ClientOnly` element with fallback and children, mock `ENVIRONMENT == "pyscript"`, render, verify children content appears and fallback is absent.
- [ ] 4.2 Test: Browser rendering without fallback — create a `ClientOnly` element with only `children`, mock `ENVIRONMENT == "pyscript"`, render, verify children content appears.
- [ ] 4.3 Test: `client_only()` generator function — verify that `client_only(children=..., fallback=...)` produces the same result as `ClientOnly(children=..., fallback=...)`.

**Estimated time**: ~1.5 hours

## 5. Unit tests for ClientOnlyElement hydration

- [ ] 5.1 Test: Hydration replaces fallback with children — create a `ClientOnly` with fallback, render SSR output first (producing fallback DOM), then call `_hydrate_node()` in browser mode, verify fallback nodes are removed and children content is rendered.
- [ ] 5.2 Test: Hydration replaces empty placeholder with children — create a `ClientOnly` without fallback, render SSR output first, then hydrate in browser mode, verify placeholder is replaced with children.
- [ ] 5.3 Test: Hydration with component containing `on_after_rendering` — verify that lifecycle hooks in `ClientOnly` children fire correctly during hydration.

**Estimated time**: ~1.5 hours

## 6. E2E test for ClientOnly full hydration flow

- [ ] 6.1 Add a `ClientOnly` demo page to the docs app E2E test app (or use an existing test page) — a page that uses `ClientOnly` with fallback content and browser-only interactive content.
- [ ] 6.2 Test: SSG output contains fallback content, not children — verify that `webcompy generate` output includes fallback HTML and excludes browser-only content.
- [ ] 6.3 Test: Browser hydration replaces fallback with actual content — verify with Playwright that after PyScript loads, the fallback is replaced with interactive children content.

**Estimated time**: ~2 hours

## 7. Verification

- [ ] 7.1 Run lint: `uv run ruff check .`
- [ ] 7.2 Run type check: `uv run pyright`
- [ ] 7.3 Run unit tests: `uv run python -m pytest tests/ --tb=short`
- [ ] 7.4 Run SSG: `uv run python -m webcompy generate --config docs_app.webcompy_config`