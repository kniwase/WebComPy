# Tasks

## 1. Spike — failing test for merged-text hydration

- [x] 1.1 Construct a unit test (new `tests/test_hydration_text_merge.py`) that builds an element tree with adjacent text-bearing children, simulates a browser-parsed DOM where the `#text` nodes are merged into one, runs `_hydrate_node`, and asserts the post-hydration DOM has a 1:1 child correspondence (fails before the fix)
- [x] 1.2 Confirm the spike fails on the current `ElementWithChildren._hydrate_node` with a concrete index-drift assertion, locking the contract before implementation

## 2. `FakeDOMNode.splitText` support

- [x] 2.1 Implement `splitText(offset)` on `FakeDOMNode` in `packages/webcompy-testing/src/webcompy_testing/_dom.py`: truncate receiver to `textContent[:offset]`, create and insert a new `FakeDOMNode("#text", text_content=textContent[offset:])` into the parent's `childNodes` after the receiver, return the new node (standard DOM `Text.splitText` contract)
- [x] 2.2 Unit-test `splitText` directly: offset splits content correctly; the new node is inserted at the right sibling position; out-of-range offset raises (matching browser behavior)

## 3. Normalization helper + both hydration loops

- [ ] 3.1 Add a shared text-run normalization helper in `packages/webcompy/src/webcompy/elements/types/_base.py` and call it from BOTH `ElementWithChildren._hydrate_node` (`_base.py`) and `DynamicElement._hydrate_node` (`packages/webcompy/src/webcompy/elements/types/_dynamic.py`): collect consecutive `TextElement` children whose DOM `#text` was merged, compute cumulative expected-text boundaries, and call `splitText` to restore per-child DOM nodes before per-child `_hydrate_node()` proceeds (dynamic containers are required — `RepeatElement` items and `FragmentElement` bodies hydrate through `DynamicElement._hydrate_node`)
- [ ] 3.2 Implement the content-equality guard (skip + fall back when `dom.textContent != concat(expected)`) and the idempotency fast path (no split when DOM already 1:1)
- [ ] 3.3 Verify the group-1 spike now passes; ensure no-merge common path still hydrates identically (regression guard on `tests/test_full_hydration.py`)

## 4. Fragment-body + keyed-reconcile unit tests

- [ ] 4.1 Add unit tests: fragment body (element + adjacent text + element) hydrating with merged DOM text; `NewLine` and `RawHTML` run-boundary handling; empty `TextElement` (`""`) no-op; content-mismatch fallback (no split, no exception)
- [ ] 4.2 Add a keyed `ReactiveDict` loop hydration test: composite item body hydrates correctly, then a reorder mutation reconciles children to the correct DOM positions with no empty/stray nodes (use `TestRenderer`/`FakeDOMNode`)

## 5. E2E regression — composite body + parity fixture

- [ ] 5.1 Restore the dict loop in `e2e/core/my_app/pages/template_control_flow.py` (line 64) to a composite item body (multiple elements + text), removing the single-element-body workaround
- [ ] 5.2 Extend `e2e/core/my_app/parity_fixtures.py` (or add a fixture) with a merged-text-node case proving the element-tree-vs-browser-DOM node-count divergence, and assert the e2e hydration path normalizes it (`e2e/core/test_template_control_flow.py` / `test_html_parser_parity.py`)

## 6. Full verification

- [ ] 6.1 Run `uv run ruff check .` and `uv run ruff format --check .`; fix any findings
- [ ] 6.2 Run `uv run pyright`; resolve any new type warnings
- [ ] 6.3 Run `uv run python -m pytest tests/ --tb=short`; ensure no regressions
- [ ] 6.4 Run `scripts/run-e2e-tests.sh <relevant-group>` (template-control-flow / html-parser-parity); confirm green

## 7. Spec / Review-skill maintenance

- [ ] 7.1 Confirm the `elements` spec delta and the File→Spec Mapping entry for `webcompy/elements/` remain consistent (no main-spec edit required until archive)
- [ ] 7.2 Update `.opencode/skills/webcompy-review/SKILL.md` Critical Framework Invariants to note the hydration text-node normalization invariant, per the config.yaml spec-change rule
