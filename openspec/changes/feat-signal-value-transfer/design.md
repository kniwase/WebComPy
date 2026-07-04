# Design: Signal Value Transfer

## Context

The hydration data transfer mechanism (`feat-suspense-and-hydration-data-transfer`) transfers `AsyncResult` states and `FetchPort` response caches from server to browser. However, application-level `Signal` values — the primary state primitive in WebComPy — are not transferred. This causes a flash of default values during hydration for any component that derives UI from Signals.

Key infrastructure already in place:
- `SignalReceivable.__signal_members__` auto-tracks all Signal instances assigned to `self` attributes via `__setattr__`.
- The codec engine (`feat-transfer-codec`) provides type-preserving serialization.
- `collect_transfer_data()` already walks the component tree for AsyncResult collection.

The challenge is: keying (the current `id()`-keyed registry is unstable across environments), Computed handling (recompute vs cached value), and restoration timing (after setup, before first render).

## Goals / Non-Goals

**Goals:**

- Automatically collect all `self`-assigned Signal values from the component tree during SSR.
- Transfer them via the codec engine with type fidelity.
- Restore them on the browser after component setup, eliminating the flash of defaults.
- Include `Computed` cached values (option 2: transfer cached value, skip recompute on restore).

**Non-Goals:**

- Transferring local (non-`self`) Signal variables.
- Transferring the reactive dependency graph (rebuilt during setup).
- Triggering notifications on restore (direct `_value` set, no `set_value()`).
- Payload compression.

## Architecture Overview

```
┌──────────────────── SERVER (SSR/SSG) ─────────────────────┐
│                                                            │
│  await ctx._root._render()                                 │
│      └─ Component setup creates Signals on self            │
│         self.count = Reactive(5)                           │
│         self.doubled = Computed(lambda: self.count * 2)    │
│                                                            │
│  await scheduler.await_pending()                           │
│      └─ Async-resolved values settled                      │
│                                                            │
│  collect_transfer_data(root):                              │
│      for each Component in tree:                           │
│          for name, signal in component.__signal_members__: │
│              signals[component_id][name] = encode(signal._value)│
│                                                            │
│  TransferPayload v2:                                       │
│      { fetches, async_results, signals }                   │
└────────────────────────┬───────────────────────────────────┘
                         │ HTML + <script> payload
                         ▼
┌──────────────────── BROWSER (PyScript) ───────────────────┐
│                                                            │
│  app.run()                                                 │
│      └─ Read payload from <script id="__webcompy_data__">  │
│      └─ Deserialize payload (decode via codec)             │
│      └─ ctx._root._render()                                │
│          └─ Component setup (creates Signals with defaults)│
│             self.count = Reactive(0)                       │
│             self.doubled = Computed(...) → evaluates to 0  │
│                                                            │
│      └─ restore_signal_values(component, signals_data):    │
│          for name, encoded_value in signals_data.items():  │
│              signal = component.__signal_members__[name]   │
│              signal._value = decode(encoded_value)         │
│          # count restored to 5, doubled restored to 10     │
│          # (direct _value set, no notification)            │
│                                                            │
│      └─ First render uses restored values (no flash)       │
└────────────────────────────────────────────────────────────┘
```

## Decisions

### D1: `__signal_members__` keyed by attribute name (not id)

The current `WeakValueDictionary` uses `id(value)` as the key — unstable across server/browser memory spaces. This change switches to a regular `dict` keyed by attribute name:

```python
# Before
__signal_members__: WeakValueDictionary[int, SignalBase]  # {id(signal): signal}

# After
__signal_members__: dict[str, SignalBase]  # {attr_name: signal}
```

`__set_signal_member__` is called from `__setattr__(name, value)`, which already has the `name`. The method signature gains a `name` parameter.

**Backward compatibility**: `__purge_signal_members__()` iterates `.values()`, unaffected by the key type. No public code accesses `__signal_members__` keys directly.

**Alternatives considered:**
- **Keep `id()` keys, add a parallel name registry**: Doubles bookkeeping. Rejected.
- **Use `WeakValueDictionary` with string keys**: `WeakValueDictionary` supports any hashable key, but weak references to Signals could be GC'd before collection runs. A regular dict keeps strong references until `__purge_signal_members__()` is called. Safer for collection timing.

### D2: Computed cached value transfer (option 2)

`Computed` signals store their cached result in `_value`. During SSR, this value is already computed (the render read it). This change transfers the cached `_value` directly:

```
  Server: Computed._value = 10  (already computed during render)
          → transfer {"doubled": encode(10)}

  Browser: Component setup creates Computed → evaluates to 0 (default source)
           Restore: Computed._value = 10  (overwritten, no recompute)
           → First render reads 10 (correct, no flash)
           → When source changes via user interaction, normal recompute kicks in
```

**Why not option 1 (source-only transfer + force recompute)?**
- Requires distinguishing source Signals from Computed Signals during restore.
- Requires a "force recompute" mechanism after source restoration.
- Ordering complexity: sources must be restored before Computed recompute.
- Option 2 is simpler: transfer everything, restore everything, no recompute logic.

**Trade-off**: The transferred Computed value is a "stale cache" until a source changes. This is acceptable because:
1. The value was correct at SSR time.
2. If no source changes, the value is still correct.
3. If a source changes, the normal reactive graph recomputes.

### D3: Direct `_value` set on restore (no notification)

Restoration sets `signal._value = decoded_value` directly, bypassing `set_value()`. This means:
- No notifications are fired during restore.
- Downstream consumers are not triggered.
- `Computed` signals do not recompute.

This is correct because all values (sources and Computed) are restored from the same coherent SSR snapshot. There is nothing to recompute — the entire state is consistent.

If `set_value()` were used, it would trigger a cascade of notifications and recomputations during restore, which is wasteful and could cause render thrashing.

### D4: Restoration timing — after setup, before first render

Signal restoration SHALL occur after component setup completes (Signals exist on `self`) and before the first render reads them:

```
  Component._render():
      1. __setup()  ← creates Signals with defaults
      2. restore_signal_values(self, payload.signals.get(self._id))
         ← overwrites _value with transferred values
      3. on_before_rendering hooks
      4. template evaluation ← reads restored values, no flash
```

**Integration point**: The restoration is called from `Component._render()` (or a hook within it), after `__init_component()` / `__setup()` completes and before template evaluation.

### D5: Collection timing — after await_pending, before dispose

On the server, Signal value collection SHALL occur after `await scheduler.await_pending()` (so async-resolved Signal values are settled) and before `ctx.dispose()`:

```
  generate_html():
      await ctx._root._render()
      await scheduler.await_pending()       ← async values settled
      payload = collect_transfer_data(root) ← collects Signals + AsyncResults
      ctx.dispose()
```

### D6: TransferPayload version 2

The `signals` section is added to `TransferPayload`. The `__webcompy_transfer_version__` bumps to `2`. The `deserialize_payload()` function checks the version:
- Version 1: ignores `signals` section (forward compatibility — a v1 browser skips unknown sections).
- Version 2: parses `signals` section.

### D7: ReactiveList and ReactiveDict serialization

`ReactiveList` and `ReactiveDict` extend `SignalBase` and store their value in `_value` (a list or dict). They are collected and restored the same way as `Signal`:
- `encode(reactive_list._value)` → list with type tags for non-JSON elements.
- `restore: reactive_list._value = decode(encoded)`.

No special handling needed — their `_value` is a plain list/dict that the codec handles.

## Risks / Trade-offs

- **[Local variables not transferred]** → Mitigation: Document that only `self`-assigned Signals are transferred. This matches the existing `__signal_members__` scope. Developers who need transfer for local Signals should assign them to `self`.

- **[Computed stale cache]** → Mitigation: The stale cache is correct until a source changes. When a source changes (user interaction), the normal reactive graph recomputes. Documented behavior.

- **[Non-serializable Signal values]** → Mitigation: The codec drops non-serializable values with a warning (best-effort). The Signal falls back to its default value on the browser.

- **[`__signal_members__` key type change]** → Mitigation: Internal API, no public consumers of the key. `__purge_signal_members__` is unaffected. Unit tests verify no regression.

- **[Payload size increase]** → Mitigation: Only `self`-assigned Signals are included. For large Signal values, `feat-payload-compression` addresses size. The codec's type tags add minimal overhead for plain JSON values (no tags).

- **[Component ID stability]** → Mitigation: Component IDs (`_property["component_id"]`) are derived from the component tree structure (MD5 hash). As long as the same tree is rendered (hydration guarantee), IDs match. This is the same stability assumption used by AsyncResult transfer.

## Open Questions

1. **Should restoration happen in `Component._render()` or in a separate post-setup hook?** Integrating into `_render()` after `__init_component__` is the simplest. A dedicated hook (e.g., `_restore_signals()`) would be cleaner but adds lifecycle complexity. Decision: integrate into `_render()` with a clearly marked restoration block.

2. **Should the `signals` section be optional in the payload?** Yes — payloads without Signals (e.g., components with no `self`-assigned Signals) produce an empty `signals: {}` section. This is harmless and keeps the schema uniform.

3. **What about Signals created in `on_before_rendering` hooks?** These hooks run after setup but before template evaluation. There are two phases to consider:

   - **Collection (SSR side):** Collection happens after the full render (after `await_pending`), so Signals created or mutated in `on_before_rendering` hooks have their final values captured correctly.
   - **Restoration (browser side):** Restoration happens after `__setup()` / `__init_component()` completes and **before** `on_before_rendering` hooks execute. If a Signal is first created (assigned to `self`) inside an `on_before_rendering` hook, it does not yet exist at restoration time, so its value cannot be restored on the **first** hydration cycle. The hook runs with the Signal at its default value. On **subsequent** hydration cycles (navigations within the SPA), the Signal exists and its transferred value is available.

   **Limitation to document:** Signals first created in `on_before_rendering` hooks are captured for transfer, but on the initial hydration their transferred values are not restored (the Signal does not exist yet at restoration time). They behave correctly on subsequent navigations. Developers who need server-computed values available immediately in such hooks should create the Signal in `__setup()` instead.
