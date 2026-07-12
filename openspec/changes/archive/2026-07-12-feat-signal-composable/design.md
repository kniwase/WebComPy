## Context

The `signal-value-transfer` feature (PR #194) was designed around `SignalReceivable.__setattr__` which auto-tracks `self.X = Signal()` assignments into `__signal_members__`. However, the class-style component API was removed in PR #96, and the current function-style API passes `context` (not `self`) to the user's setup function. Users cannot write `self.count = Signal(0)` — `self` is not defined.

As a result, `__signal_members__` is never populated for any user component. `collect_transfer_data()` collects zero signals. The feature is dead code.

Industry research confirms that no major SSR framework (React/Next.js, Vue/Nuxt, Angular, Svelte/SvelteKit) transfers arbitrary component state automatically. All require explicit opt-in via dedicated APIs (`useState`, `TransferState`, `hydratable`). The `use_state()` composable follows this industry consensus.

The existing `use_async_result` composable already solves the analogous problem for async data: it checks `HYDRATION_DATA_KEY` during setup and skips execution if a transferred value exists. The `use_state()` composable applies the same pattern to synchronous signal values.

Additionally, `ReactiveList` and `ReactiveDict` provide mutation ergonomics (`append()`, `pop()`, etc.) that trigger change events. Users who want both transfer AND mutation ergonomics need dedicated composables: `use_reactive_list()` and `use_reactive_dict()`.

## Goals / Non-Goals

**Goals:**
- Provide type-safe composables (`use_state()`, `use_reactive_list()`, `use_reactive_dict()`) that create transferable signal instances
- Implement factory-skip: server runs factory, browser restores from payload during setup
- Eliminate the `_restore_signals()` mechanism (superseded by factory-skip)
- Maintain backward compatibility with `collect_transfer_data()` (unchanged collection path)

**Non-Goals:**
- Deprecating the `Signal` class (it remains as the return type)
- Module-level (outside component) signal transfer (use `provide`/`inject` instead)
- Changing the payload format or codec

## Decisions

### Decision 1: Factory function as the sole creation API

**Choice**: `use_state(factory: Callable[[], T]) -> Signal[T]` — the factory is always a zero-argument callable, never a direct value.

**Rationale**: The factory-skip mechanism requires a callable to skip. If the user passes a direct value (`use_state(0)`), there's nothing to skip — the value is always used. By requiring a factory, the API makes the "server-only initialization" semantic explicit. This matches Nuxt's `useState(key, () => init)`.

The factory MUST be a zero-argument callable (`Callable[[], T]`). Callables that require arguments (e.g., `Callable[[int], T]`) SHALL be rejected at the type-checker level via `@overload` signatures and at runtime by raising `TypeError` before transfer registration when the callable is not zero-argument-compatible.

**Alternative considered**: Accept both `use_state(0)` and `use_state(lambda: 0)`. Rejected because `callable` check creates ambiguity when the value itself is callable.

### Decision 2: Separate composables for collections

**Choice**: `use_reactive_list(factory: Callable[[], list[V]]) -> ReactiveList[V]` and `use_reactive_dict(factory: Callable[[], dict[K, V]]) -> ReactiveDict[K, V]` as separate composables.

**Rationale**: Auto-promoting `use_state(lambda: [1,2,3])` to `ReactiveList` would surprise users who just want to transfer a plain list value. Separate composables make the intent explicit: `use_state()` returns `Signal[T]`, `use_reactive_list()` returns `ReactiveList[V]`. Each composable creates the correct type on both factory-run and factory-skip paths.

**Alternative considered**: Single `use_state()` with auto-type-detection. Rejected because implicit promotion is surprising and hard to express in type annotations.

### Decision 3: Factory-skip replaces `_restore_signals()`

**Choice**: Remove `_restore_signals()` from `_render()`. Restoration happens during setup when composables check `HYDRATION_SIGNAL_DATA_KEY` and skip the factory.

**Rationale**: This eliminates the lifecycle hook overwrite problem (restored values were overwritten by hooks running after `_restore_signals()` in `_render()`). With factory-skip, the value is correct from the moment the signal is created — before any hooks run.

**Alternative considered**: Keep `_restore_signals()` as a fallback. Rejected because it reintroduces the timing problem and creates two restoration paths.

### Decision 4: Registration via `Context._transferable_signals`

**Choice**: Composables register the created signal in `context._transferable_signals[key]`. After setup, `__setup()` merges this dict into `self.__signal_members__`.

**Rationale**: This mirrors the existing `use_async_result` → `context._async_results` pattern. The collection mechanism (`collect_transfer_data()` walking `__signal_members__`) stays unchanged.

### Decision 5: No deprecation warning for `Signal()` direct construction

**Choice**: `Signal.__init__()` does NOT emit any warning. Direct construction is fully supported for third-party subclasses, test helpers, and dynamic construction paths. No `_create()` bypass classmethods are needed.

**Rationale**: Adding a `UserWarning` to `Signal.__init__()` would penalize legitimate third-party subclasses, test helpers, and dynamic construction paths. The composable-based path (`use_state()`) is the recommended pattern for SSR transfer, but `Signal()` remains the standard constructor with no deprecation. Internal framework code uses `Signal()` directly — there is no functional difference between `Signal(value)` and a hypothetical `Signal._create(value)`, so the bypass was unnecessary.

### Decision 6: Auto-key via `inspect` + `dis`

**Choice**: When key is omitted, generate `file:line:column` from the caller's frame using `inspect.currentframe()` and `dis.get_instructions()` with Python 3.12+ instruction position metadata.

**Rationale**: Nuxt uses compiler-transformed auto-keys (file:line). WebComPy (Python) uses runtime `inspect` instead. Column number disambiguates same-line calls. Fallback to `file:line` if `dis` is unavailable (e.g., PyScript limitations).

**Risk**: PyScript/Pyodide may not support `dis.get_instructions()` or `instr.positions`. Mitigation: spike task to verify; fallback to `file:line` or sequential counter.

### Decision 7: Graceful degradation outside component context

**Choice**: When `_active_component_context.get(None)` returns `None` (outside setup), composables emit a `UserWarning` ("use_state() called outside component setup; signal will not be transferred") and create a signal without transfer registration. No error is raised.

**Rationale**: If composables errored outside components, users could not create module-level signals or signals in utility functions. However, silently succeeding makes SSR debugging difficult — the signal works but is never transferred. A `UserWarning` on first occurrence strikes a balance: developers are alerted during development, while production code can suppress it via `warnings.filterwarnings` when intentional (e.g., shared utility functions). The "first occurrence" behavior is achieved by Python's `warnings` module default behavior — `warnings.warn(msg, UserWarning)` called repeatedly for the same message and location is only shown once by default, so no additional deduplication logic is needed.

This matches Vue's `ref()` and Angular's `signal()` behavior — they work outside components but don't participate in SSR transfer.

## Risks / Trade-offs

- **[PyScript inspect compatibility]** `inspect.currentframe()` and `dis.get_instructions()` may not work in PyScript/Pyodide. → Mitigation: spike task in Phase 1; fallback to `file:line` or sequential counter key.

- **[Factory always required]** Users must write `use_state(lambda: 0)` instead of `Signal(0)`. → Mitigation: minimal overhead; lambda is a common Python idiom; Nuxt uses the same pattern.

- **[Computed not transferable]** The design follows "transfer sources, not derivations" — `use_state()` creates `Signal[T]`, not `Computed[T]`. Transferring `Computed` would cause stale values on re-evaluation. Phase 3 (`refactor-signal-api-unification`) introduces `use_computed(factory: Callable[[], T]) -> Computed[T]` as the renamed `computed()` composable. Its signature mirrors `use_state()`: zero-argument factory, auto-key or explicit key, but NO factory-skip (Computed always recomputes from transferred sources). → Mitigation: document that `use_computed()` values recompute from transferred sources.

- **[Three composables]** Users must choose between `use_state()`, `use_reactive_list()`, and `use_reactive_dict()`. → Mitigation: each has a clear purpose; naming makes intent obvious; `use_state()` is the default choice for non-collection values.

- **[Double extraction with Phase 1]** Phase 1 adds re-extraction of `_transferable_signals` after async body resolution. Phase 2 adds the initial extraction in `__setup()`. Both are idempotent. → Mitigation: extraction is a dict merge — running twice is harmless.

## Open Questions

- Should `HYDRATION_SIGNAL_DATA_KEY` be the same key used by the current `_restore_signals()` mechanism, or a new key? **Tentative answer: same key** — the payload structure is unchanged, only the consumption timing changes.
