## Context

WebComPy already has list reconciliation via `ListMutation` + `repeat(ReactiveList, template, key=)`. `ReactiveDict` however lacks mutation metadata and cannot be used with `repeat()`. Developers working with key-value data (todos with UUIDs, number→label maps) must convert to `ReactiveList`, losing the ability to do keyed reconciliation naturally. Since dict keys are inherently unique identifiers, they map directly to reconciliation keys — no separate `key` function is needed.

The current implementation stores children state in `RepeatElement` via `_key_to_child` and `_children_keys`, which assume list items with an optional key extractor. For dict mode, the template receives `(key, value)` instead of `(item,)`, and iteration order follows `dict.__iter__()` (insertion order in Python 3.7+).

## Goals / Non-Goals

**Goals:**
- Add `DictMutation` dataclass with operation metadata (`set`, `delete`, `pop`, `clear`) mirroring `ListMutation`
- Add `_last_mutation` attribute to `ReactiveDict` on each mutating method call
- Add `repeat(ReactiveDict, template)` overload where template signature is `(K, V) -> ChildNode` and K (str | int) serves as the reconciliation key
- Update docs examples (FizzBuzz, ToDo List) to demonstrate dict-based repeat with efficient reconciliation
- Add comprehensive unit and E2E tests

**Non-Goals:**
- Per-key reactive subscriptions inside `ReactiveDict` (full-collection notification remains)
- `DictMutation` for `update()` method (can be added later)
- Changing the existing `repeat(ReactiveList, ...)` API
- Dict-specific reconciliation optimizations beyond what keyed reconciliation already provides

## Decisions

### Decision 1: DictMutation mirrors ListMutation pattern
`DictMutation` uses the same dataclass pattern as `ListMutation` — simple, predictable, and consistent. Operations tracked: `set` (key-value pair added/updated), `delete` (key removed), `pop` (key removed with return value), `clear` (all entries removed). The `key` field replaces `index` from `ListMutation` since dicts are keyed, not indexed.

**Alternative considered:** Reuse `ListMutation` for both. Rejected because the semantics differ (key vs index, different ops like `set` vs `append`).

### Decision 2: Dict keys are the reconciliation keys
When `repeat()` receives a `ReactiveDict`, no separate `key` function is needed — the dict key IS the reconciliation key. This simplifies the API and avoids the possibility of duplicate keys (dict keys are inherently unique).

**Alternative considered:** Allow an optional `key` function for dict mode too, extracting a sub-key from V. Rejected as over-engineering; if the user needs a sub-key, they can restructure their dict.

### Decision 3: Template signature is `(K, V) -> ChildNode`
For dict mode, the template receives both the key and value, enabling rendering that uses the key (e.g., displaying a number in FizzBuzz, or using a UUID as an element attribute). The value parameter provides the rendering data.

**Alternative considered:** Template signature `(V,) -> ChildNode` with key available via closure. Rejected because the key is often needed in rendering (e.g., `html.LI({}, f"{k}: {v}")`).

### Decision 4: RepeatElement detects input type at construction
`RepeatElement.__init__` will check whether the `sequence` argument is `ReactiveList` or `ReactiveDict` and store a mode flag. This affects how `_refresh` and `_reconcile_children` iterate items and extract keys. No new subclass — a single `RepeatElement` handles both, branching internally.

**Alternative considered:** Separate `DictRepeatElement` subclass. Rejected because the reconciliation logic is nearly identical; the only differences are iteration (`.items()` vs `enumerate()`) and key extraction (dict key vs `key()` function). A single class with a mode flag is simpler.

### Decision 5: Dict iteration order ensures stable DOM order
Python 3.7+ guarantees dict insertion order. `RepeatElement` iterates via `dict.items()`, so DOM order follows insertion order. This matches user expectations and provides deterministic reconciliation.

## Risks / Trade-offs

- **Risk:** `ReactiveDict.__setitem__` fires for both new keys and existing-key updates, but `DictMutation(op="set")` doesn't distinguish. → **Mitigation:** The reconciliation algorithm treats "set" as "ensure this key exists in the DOM" — if the key is already rendered, the existing element is reused; if not, a new one is created. This is correct for both insert and update cases.

- **Risk:** `ReactiveDict.clear()` removes all items, triggering full-rebuild in reconciliation. → **Mitigation:** This is equivalent to the list `clear()` behavior and is acceptable.

- **Risk:** Type complexity in `repeat()` — accepting both list and dict overloads increases the type surface. → **Mitigation:** Use `@overload` decorators to make the type signatures clear for static analysis.

- **Trade-off:** Template arity differs between list mode `(T,)` and dict mode `(K, V)`. This is inherent to the data shape difference and documented clearly in the API.