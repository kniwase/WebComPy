## Context

WebComPy already has list reconciliation via `ListMutation` + `repeat(ReactiveList, template, key=)`. `ReactiveDict` however lacks mutation metadata and cannot be used with `repeat()`. Developers working with key-value data (todos with UUIDs, number→label maps) must convert to `ReactiveList`, losing the ability to do keyed reconciliation naturally. Since dict keys are inherently unique identifiers, they map directly to reconciliation keys — no separate `key` function is needed.

The current implementation stores children state in `RepeatElement` via `_key_to_child` and `_children_keys`, which assume list items with an optional key extractor. For dict mode, the template receives `(value, key)` instead of `(item,)`, and iteration order follows `dict.__iter__()` (insertion order in Python 3.7+).

## Goals / Non-Goals

**Goals:**
- Add `DictMutation` dataclass with operation metadata (`set`, `delete`, `pop`, `clear`) mirroring `ListMutation`
- Add `_last_mutation` attribute to `ReactiveDict` on each mutating method call
- Add `repeat(ReactiveDict, template)` overloads where template signature is `(V, K) -> ChildNode` or `(V,) -> ChildNode`, and K (str | int) serves as the reconciliation key
- Add `repeat(ReactiveList, template, key=)` overload where template signature is `(V, K) -> ChildNode` and K is extracted by the key function
- Add `repeat(ReactiveList, template)` overload where template signature is `(V, int) -> ChildNode` receiving the list index
- Update docs examples (FizzBuzz, ToDo List) to demonstrate dict-based repeat with efficient reconciliation
- Add comprehensive unit and E2E tests

**Non-Goals:**
- Per-key reactive subscriptions inside `ReactiveDict` (full-collection notification remains)
- `DictMutation` for `update()` method (can be added later)
- Changing the existing `repeat(ReactiveList, (V,) -> ...)` without `key` API (fully backward compatible)
- Dict-specific reconciliation optimizations beyond what keyed reconciliation already provides

## Decisions

### Decision 1: DictMutation mirrors ListMutation pattern
`DictMutation` uses the same dataclass pattern as `ListMutation` — simple, predictable, and consistent. Operations tracked: `set` (key-value pair added/updated), `delete` (key removed), `pop` (key removed with return value), `clear` (all entries removed). The `key` field replaces `index` from `ListMutation` since dicts are keyed, not indexed.

**Alternative considered:** Reuse `ListMutation` for both. Rejected because the semantics differ (key vs index, different ops like `set` vs `append`).

### Decision 2: Dict keys are the reconciliation keys
When `repeat()` receives a `ReactiveDict`, no separate `key` function is needed — the dict key IS the reconciliation key. This simplifies the API and avoids the possibility of duplicate keys (dict keys are inherently unique).

**Alternative considered:** Allow an optional `key` function for dict mode too, extracting a sub-key from V. Rejected as over-engineering; if the user needs a sub-key, they can restructure their dict.

### Decision 3: Template signature is `(V, K) -> ChildNode` (value first, key second)
For dict mode, the template receives both the value and key, with value first. This matches the natural iteration order of `(k, v) for k, v in dict.items()` but reorders to `(v, k)` so that the value — the primary rendering data — comes first. This also provides a consistent two-argument pattern across all keyed modes (dict, list+key, list+index).

A single-arg dict mode `(V,)` is also provided as overload 1 for cases where the key is not needed in rendering.

**Alternative considered:** Template signature `(K, V) -> ChildNode` (key first). Rejected because the value is the primary rendering data and should come first. The `(V, K)` order also parallels how `enumerate()` provides `(item, index)` with the data first.

**Alternative considered:** Template signature `(V,) -> ChildNode` only. Rejected because the key is often needed in rendering (e.g., `html.LI({}, f"{k}: {v}")`) and providing `(V, K)` gives developers access to it.

### Decision 4: 5-overload type-safe API via @overload decorators
`RepeatElement.__init__` and `repeat()` use 5 `@overload` signatures for precise type inference:

1. `ReactiveDict[K, V]`, template: `(V,) -> ChildNode` — dict value-only
2. `ReactiveDict[K, V]`, template: `(V, K) -> ChildNode` — dict value+key
3. `ReactiveList[V]`, template: `(V,) -> ChildNode` — list unkeyed (backward compat)
4. `ReactiveList[V]`, template: `(V, int) -> ChildNode` — list with index
5. `ReactiveList[V]`, template: `(V, K) -> ChildNode`, key: `(V) -> K` — list with key function

Internally, the implementation uses `_two_arg_template` and `_single_arg_template` attributes to dispatch at runtime, with `_call_template(v, k)` providing a unified call site. This avoids `inspect.signature()` probing and keeps runtime dispatch explicit.

**Alternative considered:** Single catch-all implementation with `Callable[..., Any]`. Rejected because it loses all type safety for callers.

### Decision 5: RepeatElement uses internal mode flags instead of subclassing
`RepeatElement.__init__` detects `ReactiveDict` input and stores `_is_dict`, `_has_key`, `_key_fn`, and template type flags. This affects how `_iter_items()`, `_populate_key_map()`, and template dispatch work. No new subclass — a single `RepeatElement` handles all modes.

**Alternative considered:** Separate `DictRepeatElement` subclass. Rejected because the reconciliation logic is nearly identical; the unified class with mode flags is simpler.

### Decision 6: Dict iteration order ensures stable DOM order
Python 3.7+ guarantees dict insertion order. `RepeatElement` iterates via `dict.items()`, so DOM order follows insertion order. This matches user expectations and provides deterministic reconciliation.

## Risks / Trade-offs

- **Risk:** `ReactiveDict.__setitem__` fires for both new keys and existing-key updates, but `DictMutation(op="set")` doesn't distinguish. → **Mitigation:** The reconciliation algorithm treats "set" as "ensure this key exists in the DOM" — if the key is already rendered, the existing element is reused; if not, a new one is created. This is correct for both insert and update cases.

- **Risk:** `ReactiveDict.clear()` removes all items, triggering full-rebuild in reconciliation. → **Mitigation:** This is equivalent to the list `clear()` behavior and is acceptable.

- **Risk:** Type complexity in `repeat()` — 5 overloads increase the type surface. → **Mitigation:** Each overload maps to a clear use case, and pyright resolves them unambiguously. Incorrect calls produce helpful type errors.

- **Trade-off:** Keyed list mode now uses `(V, K)` template signature instead of `(V,)`. This is a **breaking change** from the previous `(V,) -> ChildNode` with separate `key=` parameter. The breaking change is acceptable because the previous API was introduced in the same PR and has not yet been released.