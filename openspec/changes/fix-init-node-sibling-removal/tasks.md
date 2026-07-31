# Tasks: fix-init-node-sibling-removal

## 1. Core fix

- [ ] 1.1 Guard `ElementBase._init_node` in `packages/webcompy/src/webcompy/elements/types/_element.py` (line ~81-82): change the `else: existing_node.remove()` branch to `elif not getattr(existing_node, "__webcompy_node__", False): existing_node.remove()` (mirror `NewLine._init_node` in `_text.py:33`)
- [ ] 1.2 Guard `TextElement._init_node` in `packages/webcompy/src/webcompy/elements/types/_text.py` (line ~78-79): same change to its `else: existing_node.remove()` branch
- [ ] 1.3 Guard `RawHTMLElement._init_node` in `packages/webcompy/src/webcompy/elements/types/_text.py` (line ~119-120): same change to its `else: existing_node.remove()` branch

## 2. Regression tests

- [ ] 2.1 Add `tests/test_init_node_sibling_removal.py`: unkeyed `{% for %}` over `ReactiveList` with a trailing static `<p>` after `{% endfor %}` — after `items.append(...)`, the `<p>` is still present after the `<li>` elements (spec scenario 1). Verify RED before the fix
- [ ] 2.2 Same file: keyed `{% for k, v in d %}` over `ReactiveDict` with a trailing static sibling — after inserting a new key, the sibling survives (spec scenario 2)
- [ ] 2.3 Same file: `{% if %}` with non-patchable branch tags (`<span>` vs `<em>`) and a trailing static sibling — after toggling the condition both ways, the sibling survives (spec scenario 3)
- [ ] 2.4 Same file: prerender-adoption mismatch still recreates the node (spec scenario 4) — e.g., SSR HTML whose slot content tag mismatches the client tree is replaced, not kept

## 3. Verification

- [ ] 3.1 Run `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [ ] 3.2 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 3.3 Run full e2e suite via `scripts/run-e2e-tests.sh` (all groups, prod + static) and confirm all pass
- [ ] 3.4 Run `openspec validate fix-init-node-sibling-removal`
