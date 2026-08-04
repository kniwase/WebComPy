# Tasks

## 1. Regression Tests (fail before fix)

- [x] 1.1 Add a scenario to `TestDiamondTopology` in `tests/test_graph.py` that builds a diamond (`A→C, B→C, C→D`), cleans `C` within an epoch (`C.last_clean_epoch = increment_epoch()`), re-marks `C.dirty = True` (mid-sweep re-mark), then calls `producer_update_value_version(C)` and asserts `C.dirty` is `False` after the call
- [x] 1.2 Extend the scenario to simulate a second mutation (advance epoch via `increment_epoch()`) and assert that `producer_notify_consumers` collects `C` and propagates to `D` (i.e., `D.dirty` becomes `True`); confirm the test fails on the unpatched `_graph.py` and passes after the fix
- [x] 1.3 Add `test_epoch_clean_consumer_not_remarked_during_sweep` to `TestDiamondTopology`: a consumer cleaned for the current epoch is reached by the sweep's mark step and SHALL NOT be re-marked (`dirty` stays `False`) while a sibling consumer is still notified; confirm it fails without the mark-time epoch gate
- [x] 1.4 Update existing direct-notify tests in `tests/test_graph.py` to advance the epoch before `producer_notify_consumers`, matching production call order (`Signal.set_value` / `_change_event` always `increment_epoch()` first)
- [x] 1.5 Extend `test_epoch_clean_consumer_not_remarked_during_sweep` with a side consumer `e` of the cleaned node and assert `e.dirty` becomes `True`: the gate must NOT drop the notification for consumers that depend only on the skipped node; confirm it fails without the gate propagation

## 2. Fix the notification sweep

- [x] 2.1 In `packages/webcompy/src/webcompy/signal/_graph.py`, add the epoch-aware mark-time gate to `producer_notify_consumers`: skip (and clear residual `dirty` on) any collected consumer whose `last_clean_epoch` equals the current `_epoch`; the collection predicate is unchanged
- [x] 2.2 Keep `producer.dirty = False` on the `_epoch == producer.last_clean_epoch` early-return branch of `producer_update_value_version` as a defensive invariant for directly polled nodes
- [x] 2.3 Confirm the regression tests from group 1 now pass
- [ ] 2.4 Extend the gate branch to propagate: when the mark step skips a same-epoch-clean consumer, notify its consumers via `consumer_mark_dirty` (the node itself is not re-marked and its `dirty` stays `False`); the propagation is gate-checked at each level, so already-current consumers are skipped in turn and every other consumer receives exactly one notification

## 3. Integration Tests (Computed → DOM update)

- [x] 3.1 Add `test_nested_diamond_callback_fires_on_every_mutation` to `tests/test_signal.py`: a nested diamond (`source → left/right → inner → outer` with a callback on `outer`) performs two sequential mutations across epochs without intermediate reads, and the callback observes every update (`[70, 100]`)
- [x] 3.2 Add `TestComputedDiamondTextElement::test_text_updates_on_every_mutation` to `tests/test_elements_browser.py`: a `TextElement` bound to the outer `Computed` of a nested diamond updates its DOM text on every mutation (guards against silent stale UI)
- [x] 3.3 Verify both integration tests fail on the unpatched graph and pass after the fix (temporarily revert to confirm, then re-apply)
- [x] 3.4 Add `test_diamond_side_consumer_callback_fires_on_every_mutation` to `TestComputedDiamondNotification` in `tests/test_signal.py`: a callback consumer that depends only on the mid-sweep-cleaned node of a diamond receives the notification for every mutation (`[30, 40]`); confirm it fails without the gate propagation

## 4. Verification

- [x] 4.1 Run `uv run ruff check .` and `uv run ruff format --check .`; fix any findings
- [x] 4.2 Run `uv run pyright`; resolve any new type warnings
- [x] 4.3 Run `uv run python -m pytest tests/ --tb=short`; ensure no regressions across the signal and element test suites

## 5. Spec / Review-Skill Maintenance

- [x] 5.1 Confirm the `reactive` spec delta and the File→Spec Mapping entry for `webcompy/signal/` remain consistent (no main-spec edit required until archive)
- [x] 5.2 Update `.opencode/skills/webcompy-review/SKILL.md` Critical Framework Invariants to note the cleared-dirty invariant and the mark-time epoch gate on the notification sweep, per the config.yaml spec-change rule
