## 1. Type Alias Consolidation

- [ ] 1.1 Change `ChildNode` in `packages/webcompy/src/webcompy/elements/generators.py` from `ElementBase | TextElement | MultiLineTextElement | NewLine | SignalBase[Any] | str | None` to `ElementAbstract | SignalBase[Any] | str | None`
- [ ] 1.2 Update imports in `generators.py`: add `from webcompy.elements.types._abstract import ElementAbstract`; remove `ElementBase` from the existing `from webcompy.elements.types._element import` import if it is not referenced elsewhere in the file
- [ ] 1.3 Verify that `TextElement`, `MultiLineTextElement`, `NewLine`, and `ElementBase` are not referenced elsewhere in `generators.py` after the `ChildNode` change (unused imports should be removed to keep lint clean)

## 2. `_refresh_sync` Common Helper Extraction

- [ ] 2.1 Implement `_run_refresh_sync(refresh: Callable[..., Awaitable[None]], *args: Any) -> None` in `packages/webcompy/src/webcompy/elements/types/_dynamic.py` — extracts the nest_asyncio + loop.run_until_complete sync wrapper verbatim from `_switch.py:76-92` / `_repeat.py:144-160`
- [ ] 2.2 Import `_run_refresh_sync` from `_dynamic` in `_switch.py`; reduce `SwitchElement._refresh_sync` to `_run_refresh_sync(self._refresh, *args)`
- [ ] 2.3 Import `_run_refresh_sync` from `_dynamic` in `_repeat.py`; reduce `RepeatElement._refresh_sync` to `_run_refresh_sync(self._refresh, *args)`

## 3. Verification

- [ ] 3.1 Run `uv run pyright` — confirm no new type errors; existing `switch()` / `repeat()` return-type usages should become cleaner (no latent `DynamicElement` -> `ChildNode` mismatch); `_run_refresh_sync` usages type-check
- [ ] 3.2 Run `uv run ruff check .` and `uv run ruff format --check .`
- [ ] 3.3 Run `uv run python -m pytest tests/ --tb=short` — confirm no runtime regressions from either refactor
