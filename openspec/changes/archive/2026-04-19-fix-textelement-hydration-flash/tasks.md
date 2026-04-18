## 1. Fix TextElement hydration

- [x] 1.1 Update `TextElement._init_node()` in `webcompy/elements/types/_text.py` to reuse pre-rendered `#text` nodes instead of removing them. When `existing_node` is prerendered and `nodeName == "#text"`, set `node = existing_node` and `self._mounted = True`. Fall through to `createTextNode` only when no existing node matches.
- [x] 1.2 Update the known issues note in `openspec/specs/elements/spec.md` — remove the line about TextElement not hydrating pre-rendered text nodes, since it will be resolved.

## 2. Tests

- [x] 2.1 Add a test for `TextElement` hydration with a static string: when a prerendered `#text` node exists, `_init_node` SHALL return the existing node and set `_mounted = True`.
- [x] 2.2 Add a test for `TextElement` hydration with a `Signal` value: when a prerendered `#text` node exists, it SHALL be reused and subsequent Signal changes SHALL update the adopted node.
- [x] 2.3 Add a test for `TextElement` when existing node exists but is NOT prerendered: the existing node SHALL be removed and a new one created (existing behavior preserved).
- [x] 2.4 Run the full test suite (`uv run python -m pytest tests/ --tb=short`) and verify all tests pass.

## 3. Lint & type check

- [x] 3.1 Run `uv run ruff check .` and `uv run ruff format .` — fix any issues.
- [x] 3.2 Run `uv run pyright` — fix any type errors.