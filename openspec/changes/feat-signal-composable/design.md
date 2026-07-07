## Context

The `signal-value-transfer` feature (PR #194) was designed around `SignalReceivable.__setattr__` which auto-tracks `self.X = Signal()` assignments into `__signal_members__`. However, the class-style component API was removed in PR #96, and the current function-style API passes `context` (not `self`) to the user's setup function. Users cannot write `self.count = Signal(0)` — `self` is not defined.

As a result, `__signal_members__` is never populated for any user component. `collect_transfer_data()` collects zero signals. The feature is dead code.

Industry research confirms that no major SSR framework (React/Next.js, Vue/Nuxt, Angular, Svelte/SvelteKit) transfers arbitrary component state automatically. All require explicit opt-in via dedicated APIs (`useState`, `TransferState`, `hydratable`). The `signal()` composable follows this industry consensus.

The existing `use_async_result` composable already solves the analogous problem for async data: it checks `HYDRATION_DATA_KEY` during setup and skips execution if a transferred value exists. The `signal()` composable applies the same pattern to synchronous signal values.

## Goals / Non-Goals

**Goals:**
- Provide a type-safe `signal()` composable that creates transferable `Signal` instances
- Implement factory-skip: server runs factory, browser restores from payload during setup
- Eliminate the `_restore_signals()` mechanism (superseded by factory-skip)
- Maintain backward compatibility with `collect_transfer_data()` (unchanged collection path)
- Deprecate `Signal()` direct construction without removing the class

**Non-Goals:**
- Transfer `ReactiveList` / `ReactiveDict` values
- Remove the `Signal` class (it remains as the return type)
- Support module-level (outside component) signal transfer
- Change the payload format or codec

## Decisions

### Decision 1: Factory function as the sole creation API

**Choice**: `signal(factory: Callable[[], T]) -> Signal[T]` — the factory is always a callable, never a direct value.

**Rationale**: The factory-skip mechanism requires a callable to skip. If the user passes a direct value (`signal(0)`), there's nothing to skip — the value is always used. By requiring a factory, the API makes the "server-only initialization" semantic explicit. This matches Nuxt's `useState(key, () => init)`.

**Alternative considered**: Accept both `signal(0)` and `signal(lambda: 0)`. Rejected because `callable` check creates ambiguity when the value itself is callable.

### Decision 2: Factory-skip replaces `_restore_signals()`

**Choice**: Remove `_restore_signals()` from `_render()`. Restoration happens during setup when `signal()` checks `HYDRATION_SIGNAL_DATA_KEY` and skips the factory.

**Rationale**: This eliminates the lifecycle hook overwrite problem (restored values were overwritten by hooks running after `_restore_signals()` in `_render()`). With factory-skip, the value is correct from the moment the `Signal` is created — before any hooks run.

**Alternative considered**: Keep `_restore_signals()` as a fallback. Rejected because it reintroduces the timing problem and creates two restoration paths.

### Decision 3: Registration via `Context._transferable_signals`

**Choice**: `signal()` registers the created `Signal` in `context._transferable_signals[key]`. After setup, `__setup()` merges this dict into `self.__signal_members__`.

**Rationale**: This mirrors the existing `use_async_result` → `context._async_results` pattern. The collection mechanism (`collect_transfer_data()` walking `__signal_members__`) stays unchanged.

### Decision 4: `UserWarning` for `Signal()` direct construction

**Choice**: `Signal.__init__` emits `UserWarning` (not `DeprecationWarning`). Internal framework use bypasses via `Signal._create()` classmethod.

**Rationale**: `DeprecationWarning` implies "will be removed" — but the `Signal` class stays as the return type. `UserWarning` conveys "not recommended" without implying removal. The `_create()` bypass uses `object.__new__` + parent `__init__` to avoid triggering the warning, and is thread-safe (unlike `warnings.catch_warnings()`).

### Decision 5: Auto-key via `inspect` + `dis`

**Choice**: When key is omitted, generate `file:line:column` from the caller's frame using `inspect.currentframe()` and `dis.get_instructions()`.

**Rationale**: Nuxt uses compiler-transformed auto-keys (file:line). WebComPy (Python) uses runtime `inspect` instead. Column number disambiguates same-line calls. Fallback to `file:line` if `dis` is unavailable (e.g., PyScript limitations).

**Risk**: PyScript/Pyodide may not support `dis.get_instructions()` or `instr.positions`. Mitigation: spike task to verify; fallback to `file:line` or sequential counter.

### Decision 6: Graceful degradation outside component context

**Choice**: When `_active_component_context.get(None)` returns `None` (outside setup), `signal()` creates a `Signal` without transfer registration. No error.

**Rationale**: `signal()` is the recommended replacement for `Signal()`. If it errors outside components, users cannot create module-level signals or signals in utility functions. Graceful degradation matches Vue's `ref()` and Angular's `signal()` behavior.

## Risks / Trade-offs

- **[PyScript inspect compatibility]** `inspect.currentframe()` and `dis.get_instructions()` may not work in PyScript/Pyodide. → Mitigation: spike task in Phase 1; fallback to `file:line` or sequential counter key.

- **[Factory always required]** Users must write `signal(lambda: 0)` instead of `Signal(0)`. → Mitigation: minimal overhead; lambda is a common Python idiom; Nuxt uses the same pattern.

- **[Computed not transferable]** The design follows "transfer sources, not derivations" — `signal()` creates `Signal[T]`, not `Computed[T]`. Transferring `Computed` would cause stale values on re-evaluation. → Mitigation: document that `computed()` values recompute from transferred sources.

- **[Double extraction with Phase 1]** Phase 1 adds re-extraction of `_transferable_signals` after async body resolution. Phase 2 adds the initial extraction in `__setup()`. Both are idempotent. → Mitigation: extraction is a dict merge — running twice is harmless.

## Open Questions

- Should `HYDRATION_SIGNAL_DATA_KEY` be the same key used by the current `_restore_signals()` mechanism, or a new key? **Tentative answer: same key** — the payload structure is unchanged, only the consumption timing changes.
