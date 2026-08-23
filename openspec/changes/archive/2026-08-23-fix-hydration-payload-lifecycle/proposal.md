# Proposal: fix-hydration-payload-lifecycle

## Why

The hydration transfer payload (`HYDRATION_SIGNAL_DATA_KEY` / `HYDRATION_DATA_KEY`) is provided in the root DI scope at app startup and never revoked. `use_state()` / `use_async_result()` consult it on **every** component setup, not just during initial hydration. Because the payload is keyed by `generate_id(component_name)` — an MD5 of the component **name**, not the instance — any component created later (e.g., by client-side navigation) that shares a name with a component present on the initial page silently restores the initial page's stale value.

Observed in docs_app: opening `/sample/helloworld` and navigating to `/sample/fizzbuzz` keeps showing the HelloWorld source code in the `DemoDisplay` code block while the demo iframe correctly switches to FizzBuzz. The framework violates its own spec intent ("Factory runs on browser client-side navigation" in `signal-value-transfer`) whenever the initial page contained a same-named component.

Additionally, when one page renders **multiple instances** of the same component, collection last-write-wins on `signals[md5(name)]` and every instance restores the same (last) value — instance state is conflated.

## What Changes

- Close the hydration transfer payload when the initial hydration render pass completes: `use_state()` / `use_reactive_list()` / `use_reactive_dict()` / `use_async_result()` skip payload restoration for components created after the initial hydration window, running their factories instead (per the existing spec intent).
- Introduce a per-instance **transfer id** (`<md5(name)>#<ordinal>`), assigned from a per-`RenderContext` ordinal counter at component creation, used symmetrically by SSR collection and browser restoration so multiple same-name instances transfer independently. The DOM/scoped-CSS `component_id` (`webcompy-cid-*`) stays definition-stable and is untouched.
- Re-verified in browser: after the fix, SPA navigation between docs demo pages fetches and displays the correct per-page source, while initial-hydration restoration (no refetch, no flash) is preserved.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `signal-value-transfer`: Restoration is limited to the initial hydration window; payload lookup keys become per-instance transfer ids; client-side navigation always runs factories.
- `hydration-data-transfer`: The `HYDRATION_SIGNAL_DATA_KEY` / `HYDRATION_DATA_KEY` payloads gain a defined lifecycle (valid during initial hydration, closed afterwards); `use_async_result` restore is gated the same way; collection emits per-instance transfer ids.

## Impact

- `packages/webcompy/src/webcompy/app/_render_context.py` — new `_hydration_payload_closed` flag and per-name ordinal counters on `RenderContext`
- `packages/webcompy/src/webcompy/app/_root_component.py` — close the payload when the initial hydration render pass completes
- `packages/webcompy/src/webcompy/signal/_composable.py` — gate `_try_resolve_payload_key`; per-instance transfer id lookup
- `packages/webcompy/src/webcompy/components/_hooks.py` — same gating for `use_async_result` (`HYDRATION_DATA_KEY`)
- `packages/webcompy/src/webcompy/components/_libs.py`, `_component.py` — carry `transfer_id` on `Context` / `ComponentProperty`
- `packages/webcompy/src/webcompy/hydration/_collect.py` — collect keyed by per-instance transfer id
- Tests: unit coverage for lifecycle gating and multi-instance transfer; E2E coverage for demo-page SPA navigation staleness

## Known Issues Addressed

- "Component IDs are MD5 hashes — not collision-proof" (Component System): this change does not redefine the MD5-based `component_id` used for scoped CSS / diagnostics, but it removes the user-visible collision consequence for hydration transfer by introducing per-instance transfer ids for the payload path.

## Non-goals

- Replacing MD5-based `generate_id()` component ids used by scoped CSS (`webcompy-cid-*`) or hydration diagnostics.
- Changing the transfer payload wire format version or the codec; payload keys are opaque identifiers.
- Fetch-port transfer cache (`populate_from_transfer`) lifecycle — it is URL-keyed and does not exhibit this staleness class.
- Perfect transfer fidelity under trees whose client/server creation order differs (e.g., environment-conditional subtrees); such trees already break DOM hydration adoption.
