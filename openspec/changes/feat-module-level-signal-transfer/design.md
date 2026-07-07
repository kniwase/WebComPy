## Context

Phase 2 introduced `signal()` with factory-skip transfer, but only within component setup context (`_active_component_context` is set). At module level, `signal()` degrades to `Signal._create(factory())` with no transfer.

The core challenge is timing: on the browser, modules are imported by PyScript **before** `app.run()` reads the `__webcompy_data__` payload. So module-level `signal()` cannot check the payload during factory-skip — the payload isn't available yet.

```
BROWSER:
  ① PyScript imports modules → module-level signal() calls happen
     → factory runs (DI not initialized, may fail or produce wrong value)
  ② app.run() reads __webcompy_data__ → payload available
  ③ Components render → component-level signal() works (factory-skip)
```

The solution is **deferred restoration**: module-level signals are created with best-effort values at import time, and `app.run()` overwrites their values from the payload after deserialization.

## Goals / Non-Goals

**Goals:**
- Allow module-level `signal()` to register in a global registry
- Collect global registry signals during SSR
- Restore global registry signals in `app.run()` after payload deserialization
- Document the timing window limitation

**Non-Goals:**
- Making module-level factories work on the browser (they still run at import time with potentially unavailable DI)
- Supporting request-scoped DI in module-level factories (use `provide/inject` pattern instead)
- Changing the component-level transfer mechanism

## Decisions

### Decision 1: Global registry for module-level signals

**Choice**: A module-level `_global_transferable_signals: dict[str, SignalBase]` dict. When `signal()` is called with no active component context (`ctx is None`), it registers in this dict instead of skipping registration.

**Rationale**: Mirrors the `Context._transferable_signals` pattern but at global scope. The collection mechanism can walk both registries.

### Decision 2: Payload structure — use special component ID

**Choice**: Store global signals under a reserved component ID `"__global__"` in the existing `signals` dict.

**Rationale**: No payload format change needed. `signals["__global__"]["key"] = value`. The existing `collect_transfer_data()` and `deserialize_payload()` work unchanged. Only the collection and restoration logic need to know about the special ID.

**Alternative considered**: Add a separate `_global_signals` field to `TransferPayload`. Rejected because it requires a payload version bump and changes the dataclass.

### Decision 3: Deferred restoration in `app.run()`

**Choice**: After `app.run()` deserializes the payload and before the first render, it walks `_global_transferable_signals` and overwrites `signal._value` for any signal whose key is in `payload["__global__"]`.

**Rationale**: This is the same direct `_value` assignment used by the old `_restore_signals()` mechanism. It bypasses notifications (no subscribers at this point — rendering hasn't started).

**Timing window**: Between module import and `app.run()`, global signals may have incorrect values. If any code reads them during this window, it gets the wrong value. This is an inherent limitation — documented, not fixed.

### Decision 4: Factory failure handling at module level

**Choice**: If the factory fails at module import time on the browser (e.g., DI not available), `signal()` SHALL catch the exception, create a `Signal(None)` placeholder, and register it. `app.run()` will overwrite with the correct value later.

**Rationale**: Module import must not crash. A `None` placeholder is safe because it will be overwritten before rendering. If the value is NOT in the payload (no SSR), the placeholder persists — but this only happens for client-side navigation where the factory should be re-evaluated.

**Risk**: If the factory has side effects that partially execute before failing, those side effects may have already occurred. → Mitigation: document that module-level factories should be side-effect-free.

## Risks / Trade-offs

- **[Timing window]** Global signals have incorrect values between import and `app.run()`. → Mitigation: document; recommend `provide/inject` for signals that need to be read early.

- **[Global state pollution]** A global registry persists across renders. If a module is re-imported (unlikely in Python), signals would be re-registered. → Mitigation: dict overwrite is idempotent; same key replaces.

- **[Factory side effects]** Module-level factories may have side effects that run on both server and browser. → Mitigation: document that factories should be pure; the framework cannot enforce this.

- **[Concurrency]** On the server, multiple requests share the same module-level signals. → Mitigation: module-level signals are process-scoped, not request-scoped. If request-scoped data is needed, use `provide/inject`. Document this clearly.

## Open Questions

- Should module-level signal transfer be opt-in (e.g., `signal(factory, transfer=True)`)? **Tentative answer: No** — module-level `signal()` calls are already explicit; adding `transfer=True` is redundant.
- Should the `"__global__"` component ID be a named constant? **Tentative answer: Yes** — `GLOBAL_SIGNAL_COMPONENT_ID = "__global__"` in `_keys.py` or `_payload.py`.
