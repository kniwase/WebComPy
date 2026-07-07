## Why

Phase 2 (`feat-signal-composable`) introduced `signal()` with transfer support, but only when called inside a component setup function (where `_active_component_context` is set). When `signal()` is called at module level (e.g., in a shared store module imported by multiple components), it gracefully degrades to a non-transferable `Signal` — the factory always runs on both server and browser, producing potentially different values.

This creates a gap: module-level shared state that depends on server-only data (cookies, request headers, environment variables) cannot be transferred. Users must work around this by creating signals inside a root component's setup and sharing them via `provide/inject`. While that pattern works, it adds boilerplate and prevents clean module-level store patterns.

This change extends the transfer mechanism to module-level `signal()` calls, solving the timing problem (module loads before `app.run()` reads the payload) through deferred restoration.

## What Changes

- Introduce a global registry for module-level transferable signals (`_global_transferable_signals: dict[str, SignalBase]`)
- Module-level `signal()` calls register in the global registry instead of `Context._transferable_signals`
- During SSR, `collect_transfer_data()` SHALL also collect from the global registry, storing values in a `_global` section of the payload
- During browser hydration, `app.run()` SHALL restore global registry signals from the payload **after** reading `__webcompy_data__` and **before** the first render
- Module-level signals created on the browser before `app.run()` SHALL use a placeholder value (factory may fail due to uninitialized DI); after `app.run()` restores the payload, the signal value SHALL be overwritten with the transferred value
- Document the timing window: between module load and `app.run()`, module-level signals may have incorrect values; consumers should not read them during this window

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `signal-value-transfer`: Add module-level signal collection from global registry; add deferred restoration in `app.run()`; add `_global` section to payload structure
- `composables`: `signal()` SHALL detect module-level context (no active component context) and register in global registry; document the timing window limitation

## Impact

- `packages/webcompy/src/webcompy/signal/_composable.py` — `signal()` registers in global registry when `ctx is None` (instead of just returning `Signal._create(factory())`)
- `packages/webcompy/src/webcompy/hydration/_collect.py` — `collect_transfer_data()` also collects from `_global_transferable_signals`
- `packages/webcompy/src/webcompy/hydration/_payload.py` — add `_global_signals` section to `TransferPayload` (or use a special component ID like `"__global__"`)
- `packages/webcompy/src/webcompy/app/_app.py` or `_render_context.py` — `app.run()` restores global signals after payload deserialization
- `openspec/specs/signal-value-transfer/spec.md` — add module-level transfer requirements

## Known Issues Addressed

- Module-level `signal()` calls cannot transfer values → this change adds global registry and deferred restoration

## Non-goals

- Changing the component-level `signal()` transfer mechanism (unchanged from Phase 2)
- Supporting module-level `signal()` with DI-dependent factories that require request-scoped DI keys (these still need `provide/inject` pattern)
- Changing the payload version (stays at version 2; `_global` section is additive)
- Transferring `ReactiveList` / `ReactiveDict` at module level
