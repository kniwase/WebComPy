## 1. Lazy-load the `/` route in docs_app

- [ ] 1.1 Remove `from .pages.home import HomePage` from `docs_app/router.py`
- [ ] 1.2 Change `{"path": "/", "component": HomePage}` to `{"path": "/", "component": lazy("docs_app.pages.home:HomePage", __file__)}`
- [ ] 1.3 Verify the docs app dev server starts and the `/` route renders correctly

## 2. Batch lazy route preloading in Router

- [ ] 2.1 Collect all unresolved `LazyComponentGenerator` instances into a list in `Router.preload_lazy_routes()`
- [ ] 2.2 Replace per-route `setTimeout` with a single batched `setTimeout` callback
- [ ] 2.3 Run `tests/test_lazy_routing.py` to verify preload behavior is unchanged
- [ ] 2.4 Run `uv run ruff check webcompy/router/_router.py` to verify lint passes

## 3. Verification

- [ ] 3.1 Run full test suite `uv run pytest tests/ --tb=short`
- [ ] 3.2 Verify docs app loads from non-root routes (e.g., `/documents`) without eager home page import
- [ ] 3.3 Verify lint and type check pass (`uv run ruff check . && uv run pyright`)
