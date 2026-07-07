## Context

`ReactiveList` and `ReactiveDict` provide reactive collection types that extend `SignalBase`. They wrap Python `list`/`dict` operations and trigger reactive notifications on mutation. However, Python lacks JavaScript's `Proxy` mechanism, so every mutating method (`append`, `extend`, `insert`, `remove`, `pop`, `clear`, `__setitem__`, `__delitem__` for lists; `__setitem__`, `__delitem__`, `pop`, `clear`, `update` for dicts) must be manually wrapped.

This creates maintenance overhead and a conceptual mismatch with the `signal()` / `computed()` vocabulary. Additionally, the current implementation triggers full-collection change notifications on any mutation — there is no element-level diffing, making fine-grained reactive updates impossible.

Vue 3 offers both `ref([])` (whole-value replacement) and `reactive([])` (Proxy-based method interception). Angular uses `signal([])` with explicit mutation (`mutate` or `.update`). Svelte uses `$state([])` with Proxy. The question is whether WebComPy needs the method-interception model or whether `Signal[list]` with whole-value replacement is sufficient.

## Goals / Non-Goals

**Goals:**
- Enumerate all usages of `ReactiveList` and `ReactiveDict` in the codebase
- Evaluate DX trade-offs: method-level reactivity vs. whole-value replacement
- Assess whether `Signal[list]` / `Signal[dict]` can cover the same use cases
- Produce a clear recommendation: Deprecate, Retain, or Partial Deprecate
- If deprecating: document migration patterns and timeline

**Non-Goals:**
- Implementing any code changes (separate change)
- Designing a new collection reactive system
- Evaluating `Computed` derivations from collections

## Decisions

### Investigation framework

The investigation SHALL evaluate the following dimensions for each usage site:

1. **Mutation pattern**: Does the code use individual element mutations (`items.append(x)`, `items[i] = x`) or whole-collection replacement (`items.value = new_list`)?
2. **Performance sensitivity**: Is the collection large enough that whole-value replacement causes measurable overhead?
3. **Readability impact**: How much more verbose does the code become with whole-value replacement?
4. **Ecosystem alignment**: Do competing frameworks (Vue, Angular, Svelte) use method-level or whole-value patterns for similar use cases?

### Decision criteria

- **Deprecate**: If >80% of usage sites can migrate to `Signal[list]` / `Signal[dict]` with acceptable DX, and the maintenance cost of ReactiveList/Dict outweighs their value
- **Retain**: If usage sites rely heavily on method-level reactivity and whole-value replacement would significantly harm DX or performance
- **Partial Deprecate**: If ReactiveList/Dict should be retained but simplified (e.g., remove rarely-used methods, focus on core operations)

## Risks / Trade-offs

- **[Deprecation migration cost]** If the investigation recommends deprecation, existing user code using ReactiveList/Dict would need migration. → Mitigation: provide a codemod or clear migration guide; deprecation warning period before removal.
- **[Performance regression]** Whole-value replacement for large lists/dicts may cause unnecessary re-renders if downstream consumers can't diff. → Mitigation: evaluate if `Signal[list]` with equality-check short-circuiting mitigates this.
- **[Investigation scope creep]** The investigation could expand into redesigning the reactive collection system. → Mitigation: strict scope — evaluate existing types only, don't design new ones.

## Open Questions

- Are there any framework-internal usages where ReactiveList/Dict provide performance benefits that `Signal[list]` cannot match? (e.g., `ReactiveDict` in `HeadPropsStore` for title/meta management)
- Does the `dict-repeat-overload` spec (which optimizes `ReactiveDict` reconciliation with `repeat()`) create a dependency that prevents deprecation?
- Should `computed()` return `Signal[list]` or support returning `ReactiveList` for derived collections?
