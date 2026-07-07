## 1. Codebase Audit

- [ ] 1.1 Search for all `ReactiveList` instantiations across `packages/`, `docs_app/`, `tests/`, `e2e/` — record file, line, and context
- [ ] 1.2 Search for all `ReactiveDict` instantiations across the same paths
- [ ] 1.3 Search for all `ReactiveList` mutation calls (`.append`, `.extend`, `.insert`, `.remove`, `.pop`, `.clear`, `__setitem__`, `__delitem__`)
- [ ] 1.4 Search for all `ReactiveDict` mutation calls (`__setitem__`, `__delitem__`, `.pop`, `.clear`, `.update`)
- [ ] 1.5 Categorize each usage site by mutation pattern (method-level vs. whole-value replacement)
- [ ] 1.6 Identify framework-internal usages that other features depend on (e.g., `HeadPropsStore`, `dict-repeat-overload` spec)

## 2. DX Evaluation

- [ ] 2.1 Write before/after code examples for common patterns (append, remove, update item, bulk replace) showing ReactiveList vs. Signal[list]
- [ ] 2.2 Evaluate readability: how much more verbose is `items.value = [*items.value, x]` compared to `items.append(x)`?
- [ ] 2.3 Evaluate performance: does whole-value replacement for typical collection sizes (10, 100, 1000 items) cause measurable overhead in a benchmark?
- [ ] 2.4 Compare with Vue (`ref([])` vs. `reactive([])`) and Angular (`signal([])` with `.update()`) approaches

## 3. Dependency Analysis

- [ ] 3.1 Check if `dict-repeat-overload` spec creates a hard dependency on `ReactiveDict` — can `repeat()` work with `Signal[dict]` instead?
- [ ] 3.2 Check if `HeadPropsStore` (used by `AppDocumentRoot` for title/meta management) can use `Signal[dict]` instead of `ReactiveDict`
- [ ] 3.3 Check if any E2E tests depend on ReactiveList/Dict-specific behavior (e.g., `_last_mutation` metadata)
- [ ] 3.4 Document all blocking dependencies that would prevent deprecation

## 4. Recommendation

- [ ] 4.1 Calculate migration feasibility percentage (easy + moderate vs. hard + blocking)
- [ ] 4.2 Write the "Recommendation" section in design.md with outcome: Deprecate, Retain, or Partial Deprecate
- [ ] 4.3 If Deprecate: draft migration guide outline (to be expanded in the implementation change)
- [ ] 4.4 If Retain: document the rationale and any API improvements needed
- [ ] 4.5 If Partial Deprecate: list which features to keep and which to remove

## 5. Validation

- [ ] 5.1 Run `openspec validate investigate-reactive-collections`
