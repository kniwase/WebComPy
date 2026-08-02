# Tasks

## 1. Regression Test (fails before fix)

- [ ] 1.1 Add a scenario to `TestDiamondTopology` in `tests/test_graph.py` that builds a diamond (`A→C, B→C, C→D`), cleans `C` within an epoch (`C.last_clean_epoch = _epoch`), re-marks `C.dirty = True` (mid-sweep re-mark), then calls `producer_update_value_version(C)` and asserts `C.dirty` is `False` after the call
- [ ] 1.2 Extend the scenario to simulate a second mutation (advance epoch via `increment_epoch()`) and assert that `producer_notify_consumers` collects `C` and propagates to `D` (i.e., `D.dirty` becomes `True`); confirm the test fails on the unpatched `_graph.py` and passes after the fix

## 2. Fix `producer_update_value_version`

- [ ] 2.1 In `packages/webcompy/src/webcompy/signal/_graph.py`, add `producer.dirty = False` to the `_epoch == producer.last_clean_epoch` early-return branch of `producer_update_value_version` (currently lines 133-135)
- [ ] 2.2 Confirm the regression tests from group 1 now pass

## 3. Integration Test (Computed → DOM update)

- [ ] 3.1 Add an integration test (in `tests/test_signal.py` or a new `tests/test_computed_diamond.py`) that wires a `Computed` driven by two `Signal` producers to a `TextElement`/callback, performs two sequential mutations across epochs, and asserts the downstream text/callback observes every update (guards against silent stale UI)
- [ ] 3.2 Verify the integration test fails on the unpatched graph and passes after the fix (temporarily revert to confirm, then re-apply)

## 4. Verification

- [ ] 4.1 Run `uv run ruff check .` and `uv run ruff format --check .`; fix any findings
- [ ] 4.2 Run `uv run pyright`; resolve any new type warnings
- [ ] 4.3 Run `uv run python -m pytest tests/ --tb=short`; ensure no regressions across the signal and element test suites

## 5. Spec / Review-Skill Maintenance

- [ ] 5.1 Confirm the `reactive` spec delta and the File→Spec Mapping entry for `webcompy/signal/` remain consistent (no main-spec edit required until archive)
- [ ] 5.2 Update `.opencode/skills/webcompy-review/SKILL.md` Critical Framework Invariants to note the cleared-dirty invariant on the epoch early-return path, per the config.yaml spec-change rule
