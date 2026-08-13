# Design: feat-readonly-signal

## Context

WebComPy's reactive state is built on `Signal` (read/write), `Computed`/`ReadonlySignal` (read-only views), and the recently merged `signal-stream` bridges (`to_signal`, `to_reactive_list`, `to_async_iter`) that convert pull-based iterables into a writable `StreamResult.value`. There is no primitive for push-based *state* sources (window/document events, external callbacks) that yields a genuinely read-only signal, and no composable conveniences for the common browser state-event cases. The `readonly()` wrapper exists (`signal/_readonly.py`) but requires the caller to construct and hold a writable `Signal` separately.

This capability introduces (1) a context-free `use_readonly_signal` primitive returning `(ReadonlySignal, update)` — the update function being the only write path — and (2) `webcompy.events` helpers `use_window_event` / `use_document_event` that bridge `HostPort` / `DOMPort` event sources into the primitive with component-lifecycle cleanup.

Constraints from the codebase:

- `HostPort.add_window_event_listener` (`ports/_host.py`) and `DOMPort.add_document_event_listener` (`ports/_dom.py`) already return cleanup callables; browser implementations manage `ffi.create_proxy` + destroy. `ServerHostPort.add_window_event_listener` is a safe no-op (server-side, fires nothing).
- The composables spec enforces a two-tier API: public `use_*` composables from the `webcompy` top level, internal constructors from `webcompy.signal`. Context-free composables like `use_computed` and `use_counter` set the "no warning outside setup" precedent.
- Storage composables (`webcompy/storage/_composable.py`) establish the `on_before_destroy` chaining pattern for listener cleanup.
- `ReadonlySignal` is a `Computed` subclass; `readonly()` wraps a `SignalBase` and delegates value reads through a small computed node. `ReactiveList`/`ReactiveDict` derive from `Signal` and inherit this too.

## Goals / Non-Goals

**Goals:**

- Provide a context-free primitive `use_readonly_signal(initial) -> (ReadonlySignal[T], Callable[[T], None])` where `update` is the sole write path and the public type is unambiguously read-only.
- Provide `use_window_event` / `use_document_event` composables for browser state events (resize width, media-like flags, visibility, pointer state) that attach a listener only when component-lifecycle cleanup is guaranteed — no orphaned listeners or proxies (Event Handler Leaks invariant).
- Keep the design environment-deterministic: SSR/SSG render `initial`, browser behavior is identical until the event source fires.
- Reuse existing ports and lifecycle machinery exactly; no new globals, no new dependencies.
- Define behavior in the `readonly-signal` spec so every scenario is testable.

**Non-Goals:**

- Bridging occurrence-type events (clicks, keypresses, ticks). Signal equality dedup silently drops duplicate occurrences; plain callable handlers are the correct tool.
- A node/element-level event composable (`use_node_event`). Element events have existing framework support: declarative `events={}` (with proxy + ErrorBoundary + destroy lifecycle in `elements/types/_element.py`) and `:bind`; pairing them with `use_readonly_signal` is a one-line composition.
- An error/finished channel like `StreamResult`. A read-only state signal has no async pipeline; `transform` errors are contained by logging.
- Hydration transfer of readonly state.
- Changes to `signal-stream`, `reactive`, or `composables` requirements.

## Decisions

### D1: `use_readonly_signal` returns a `(ReadonlySignal, update)` tuple

**Decision.** `use_readonly_signal(initial: T)` returns `(ReadonlySignal[T], update: Callable[[T], None])`. `update` closes over a private `Signal`; the public view is `readonly(inner)`.

Alternatives considered:

- **StreamResult-style wrapper** (`.value` + `aclose()`): consistent with `to_signal`'s shape, but reintroduces a lifecycle object and three-signal machinery that state events do not need, and the writable-`Signal` precedent we deliberately avoid.
- **Bare `ReadonlySignal` plus separately returned inner `Signal`**: leaves the writable channel as a first-class object, defeating the "function-only write path" guarantee the user asked for.
- **HelloState/controller object (`result.view`, `result.update`)**: more discoverable but adds a custom type for no functional gain; the tuple mirrors the composable family (`use_counter`, `use_theme` return tuples).

Rationale: the tuple is the minimal honest shape for "read-only signal + external-only write function", matches composable conventions, and stays context-free (nothing to clean, works standalone and inside other composables).

### D2: Separate capability `readonly-signal`, separate module homes

**Decision.** The capability is a new spec indepent of `signal-stream`. Implementation splits across two module homes:

- `packages/webcompy/src/webcompy/signal/_readonly.py` — the context-free primitive (pure, no ports), exported from `webcompy.signal` and `webcompy`.
- `packages/webcompy/src/webcompy/events/` — new package (structure modeled on `webcompy/storage/`) holding the `HostPort`/`DOMPort`-coupled composables, exported from `webcompy.events` and `webcompy`.

Alternatives considered:

- **Extend `signal-stream` spec + `webcompy/aio/_stream.py`**: shared pump/cleanup machinery looks like a win, but the two differ on execution model (async pull pump vs synchronous push subscribe), return contract (writable `StreamResult` vs read-only tuple), and dedup meaning (trap vs feature). Co-location would force caveats into every requirement.
- **Put the helpers in `webcompy/aio`**: semantically wrong — the bridge is synchronous and event-driven, not an IO utility.
- **Put the helpers in `webcompy/signal`**: would import ports into the currently pure signal package.

Trade-off accepted: excluding the node helper means duplicate-with-tiny-delta code is not a factor; the only cost is a second discrete module home, which matches how `use_local_storage` already lives away from signal.

### D3: Helpers attach listeners only inside component setup

**Decision.** `use_window_event` / `use_document_event`:

- require an active component setup context to attach a listener, registering the port cleanup on `on_before_destroy` (chained via the storage composables pattern);
- otherwise (no component context) emit a `UserWarning` and attach nothing — leak-free;
- inject the port with a `None` default; a missing port (or the server `ServerHostPort` no-op) results in no real listener, keeping SSR/SSG output deterministic (`initial` rendered).

Alternatives considered:

- **Always attach and return an unsubscribe**: makes the return shape heterogeneous outside components and pushes lifecycle mistakes onto callers, contrary to the invariant.
- **Attach whenever a DI scope exists**: pairs an untracked listener with an eventual app teardown path that the port does not guarantee today; rejected on the Event Handler Leaks invariant.

Note: during SSR/SSG the component setup context *is* active, so `use_window_event` runs against `ServerHostPort`, whose `add_window_event_listener` returns a no-op cleanup — no server warning, no errant behavior. The warning path is therefore exclusive to genuinely context-free browser misuse.

### D4: Equality dedup is a documented feature, not a hazard

**Decision.** The signal equality contract applies: `update(v)` equal to the current value does not notify. This is correct for state-like events (a resized width that did not change) and is stated explicitly in the spec. Occurrence semantics belong to `to_reactive_list`/`to_async_iter` or plain handlers — called out as a non-goal rather than circumnavigated.

### D5: transform errors are contained by logging

**Decision.** Exceptions from the `transform` callable while handling a fired event are caught, logged via `webcompy.logging.warning`, and swallowed — mirroring the storage composables' non-fatal failure policy. There is no error signal; a thrown transform must not break the browser's event dispatch. The `update` call itself writes a Signal and does not raise.

### D6: Not a node-level composable (defer)

**Decision.** `use_node_event` is excluded from scope. Grounding: element event handlers already flow through `_generate_event_handler` (`elements/types/_element.py`) which pairs every `addEventListener` with `removeEventListener` + proxy `destroy()` at detach/removal; `DomNodeRef.element` raises before mount (`types/_refference.py`), so a composable would need node-availability tracking and re-subscription across reconciliation — high ceremony for what `events={}` plus `use_readonly_signal` already expresses in one line.

### D7: Test support via fake ports

**Decision.** `webcompy-testing` fakes gain listener recording/triggering so the helpers are unit-testable headlessly: the fake `HostPort`/`DOMPort` should store the handler per event type and expose a way to dispatch synthetic events (so a test can fire a `resize`, assert the signal updated, destroy the component, and assert removal). The primitive itself needs no port at all.

## Risks / Trade-offs

- **ReadonlySignal adds a computed hop** — Each `.value` access on the returned view reads through `readonly()`'s `Computed`-style wrapper. → Acceptable: it is one lazy re-read of a live `Signal` and matches how `:bind` already consumes `ReadonlySignal`; no render-path hot loop is affected more than any other computed.
- **Warning on outside-setup browser use could surprise** — A developer writing a top-level script with `use_window_event` sees a warning and a no-op. → Intended: it is the leak-avoidance signal; the doc page will show the standalone path (own listener + `use_readonly_signal`) for such cases.
- **Equality dedup visibly swallows events** — A developer bridging what is really an occurrence stream loses occurrences silently. → Mitigated by explicit spec/Docs `Why-not-occurrence` statements; `to_reactive_list` is the documented alternative.
- **File/`Scan` duplication of cleanup chaining** — The `on_before_destroy` chaining helper exists in `webcompy.storage` and `webcompy.aio._stream` in private form. → We replicate the ~10-line chain locally in `webcompy.events` rather than import a `_`-prefixed helper across packages, keeping `events` decoupled; optionally hoist a shared helper in a follow-up if a third user appears.
- **Fake ports refactor** — `FakeBrowserHostPort` currently discards the handler (returns `lambda: None`), so helper tests require a fake upgrade. → Contained to `webcompy-testing`; no production port changes.

## Migration Plan

Pure additive feature: no existing API, data, or storage changes; no dependency changes; no rollback beyond reverting the change commit. Docs update (AGENTS.md spec list, File→Spec Mapping, `check-doc-spec-refs.py` regression) ships in the same change.

## Open Questions

- Doc page placement under `docs_app` (alongside the `signal-stream` page) and whether a single page or a short section is preferred — resolved during implementation in sympathy with the existing markdown-document page structure.
- Whether `transform` should also be accepted positionally alongside `event_type`/`initial` or remain keyword-only — default choice: keyword-only to keep the two required arguments at the front.