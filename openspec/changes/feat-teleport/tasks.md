# Tasks: feat-teleport

## 1. Core element

- [ ] 1.1 Create `TeleportElement(DynamicElement)` in `packages/webcompy/src/webcompy/elements/types/_teleport.py`: store the static `to` selector; `_on_set_parent()` assigns `child._parent = self` for each child; create the single anchor placeholder node (empty text node) as the element's own node with `_node_count == 1`
- [ ] 1.2 Implement target resolution via `DOMPort.query_selector(to)` at mount time; override `_get_node()` to return the resolved target node once teleported (logical parent's node before teleportation / in inline fallback); override `_render()` to position children against the target node
- [ ] 1.3 Implement the missing-target fallback: log a warning and render children inline at the logical position (anchor replaced by children's nodes), without raising into the render tree
- [ ] 1.4 Implement removal: `_remove_element` removes teleported child nodes from the target and the anchor from the logical parent, destroying callback consumers via the standard path

## 2. Public API

- [ ] 2.1 Implement the `Teleport` constructor accepting a props dict with the `to` key plus children (`Teleport({"to": "body"}, *children)`), validating `to` is a non-empty static string
- [ ] 2.2 Export `Teleport` from `webcompy.elements` (`__init__.py` + `.pyi` if the package maintains stubs for this module)

## 3. Testing support

- [ ] 3.1 Extend `webcompy_testing` fake DOM so teleport targets are resolvable: a document-level root node addressable as `body` (or selector-configurable) that `query_selector` can match, so `TestRenderer`-based tests can assert teleported node placement

## 4. Unit tests (`tests/test_teleport.py`, browserless via TestRenderer)

- [ ] 4.1 Mount behavior: children of `Teleport({"to": "body"}, ...)` are DOM children of the fake `body`, not of the logical parent; exactly one anchor placeholder exists at the logical position
- [ ] 4.2 Sibling stability: with text–Teleport–text sequences, mutating the teleported subtree (add/remove children) leaves sibling positions correct and the anchor count constant
- [ ] 4.3 Missing target: unknown selector logs a warning and renders children inline; no exception raised
- [ ] 4.4 Multiple teleports to the same target append in mount order
- [ ] 4.5 Removal: conditional removal deletes teleported nodes from the target and the anchor from the logical parent; no orphaned nodes remain
- [ ] 4.6 Reactivity: a Signal-driven update inside teleported content mutates the node under the target; scoped-style attributes and event handler wiring remain intact on the relocated node

## 5. SSR behavior

- [ ] 5.1 Verify with the server render path (SSG/SSR test utilities) that SSR output contains only the anchor at the logical position and no teleported content anywhere; add a regression test asserting absence of the teleported markup in generated HTML

## 6. E2E and docs

- [ ] 6.1 Add an E2E test (Playwright, `e2e/`): a page with a Teleport-based modal — open renders content under `body`, close removes it, sibling content stays stable
- [ ] 6.2 Add a docs_app demo page for `Teleport` (modal + dropdown reworked onto Teleport) and link it from the docs navigation; document the target-stability constraint and the SSR anchor-only behavior

## 7. Validation

- [ ] 7.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 7.2 `uv run pyright` passes
- [ ] 7.3 `uv run python -m pytest tests/ --tb=short` passes
