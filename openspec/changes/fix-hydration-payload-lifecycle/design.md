# Design: fix-hydration-payload-lifecycle

## Context

See proposal.md - Why. Verified in browser (docs_app dev server + Playwright):

- `/sample/helloworld` SSR payload contains `signals[md5("DemoDisplay")]["docs_app.components.demo_display:22:18"] = <helloworld source>`.
- After SPA navigation to `/sample/fizzbuzz`, the new `DemoDisplay` restores that stale entry (payload never expires, key is name-based), and `DemoDisplay.load()`'s early-return guard suppresses the refetch. No main-frame request for the new demo source is ever issued.
- Starting from `/` (no `DemoDisplay` in payload) makes the same navigations work correctly, confirming the gating condition.

Existing infrastructure this design builds on:

- `RenderContext._hydration_in_progress` already brackets the hydration window for mismatch reporting (`AppDocumentRoot._render()` sets it before hydrating/rendering children and resets it in a `finally`).
- `generate_id(component_name)` (MD5 of the component name) doubles as the scoped-CSS attribute suffix (`webcompy-cid-*`), so it cannot become instance-unique.
- `component_id` in `ComponentProperty` feeds payload collection (`hydration/_collect.py`) and diagnostics (`_suspense.py`, hydration reports).

## Goals / Non-Goals

**Goals:**

- Transfer payloads restore values only during the initial hydration window; every component setup after that runs factories.
- Multiple instances of the same component on one page transfer and restore independently.
- Zero change to the wire format version, codec, scoped CSS attributes, or the fetch/resource payload sections.

**Non-Goals:**

- Cross-environment creation-order mismatches (environment-conditional trees) stay unsupported, consistent with DOM hydration adoption.
- `hydrate=False` apps: the payload never closes (no hydration render pass), preserving today's restore-on-first-render behavior.

## Decisions

### 1. Close the payload at the hydration window boundary, not consume-once

Add `RenderContext._hydration_payload_closed: bool = False`. `AppDocumentRoot._render()` sets it to `True` in the same `finally` block that resets `_hydration_in_progress`. A small helper (`_is_hydration_payload_open()`) resolves the active render context via `_active_app_context.get() or _get_app_instance()` and returns the negated flag (default: open when no context exists, preserving unit-test behavior).

- `_try_resolve_payload_key()` (`signal/_composable.py`) returns `_MISSING` when closed.
- `use_async_result()` (`components/_hooks.py`) skips the `HYDRATION_DATA_KEY` restore when closed.

**Why over consume-once per entry:** consume-once breaks legitimate double creation during hydration (e.g., error-boundary resets, re-rendered subtrees) and still mis-pairs values for multi-instance pages. Window gating matches the spec's existing intent ("Factory runs on browser client-side navigation") and has exactly one state transition.

**Why the `finally` block:** it covers failure paths (render exceptions) and the non-hydrate first render; setting the flag repeatedly on later re-renders is idempotent. The window deliberately includes the `await scheduler.await_pending(only_render=True)` drain so async component setups and Suspense resolutions that gate the reveal still restore.

**Verified by spike:** this gate alone fixes the docs_app demo bug (code block follows navigation; main-frame fetch resumes) while initial hydration still restores without a network round-trip; all 4955 unit tests pass.

### 2. Per-instance transfer id alongside, not replacing, `component_id`

`Context` gains `_transfer_id`; `ComponentProperty` gains `transfer_id`. Computed in `Component.__setup__` before the setup function runs:

```
app_ctx = _active_app_context.get() or _get_app_instance()
transfer_id = app_ctx._next_transfer_id(component_name) if app_ctx else generate_id(component_name)
```

`RenderContext._next_transfer_id(name)` increments a per-context `dict[str, int]` counter and returns `f"{generate_id(name)}#{n}"`.

- Collection (`hydration/_collect.py`) keys `signals` / `async_results` by `_property["transfer_id"]` (falling back to `component_id` for hand-built test doubles).
- Restoration (`_try_resolve_payload_key`, `use_async_result`) looks up `ctx._transfer_id`.
- `component_id` (scoped CSS, diagnostics) is unchanged.

**Why ordinals over random ids:** SSR collection and browser hydration must agree on keys without communication; per-name creation-order ordinals are deterministic on both sides because both build the same tree in pre-order (parents construct children during setup; route-level components are created at their `RouterView` position during the render pass in both environments).

**Why not DOM-anchored ids:** restoration must happen during setup (factory-skip design), before the component owns or adopts a DOM node, so DOM position cannot feed the key.

### 3. No changes to fetch cache or resource transfer

`BrowserFetchPort._response_cache` is keyed by URL (+method/body) and `RESOURCE_DATA_KEY` by path; neither collides across component instances, and both are intentionally app-lifetime caches. They keep working unchanged, which also preserves the no-refetch initial load observed in docs_app.

## Risks / Trade-offs

- **Creation-order drift between SSR and hydration** (e.g., async components resolving at different positions) → instances could restore a sibling's value. Mitigation: ordinals are assigned at construction (pre-order), and both environments construct the tree the same way; mismatched trees already fail DOM hydration adoption. Residual risk accepted and documented in the spec.
- **Testing-module / unit-test doubles** that never attach a `RenderContext` → they fall back to bare `generate_id(name)` keys, keeping existing tests and payload fixtures valid.
- **Suspense-resolved subtrees created after the reveal** (client-side async boundaries) → their `use_state()` runs after the window closes and will not restore; they render factory defaults as if client-navigated. Mitigation: SSR awaits Suspense content, and the browser drain covers render-scoped resolution; post-reveal resolution was already a client-side render.
- **`hydrate=False` apps keep the payload open** → the staleness class persists there. Mitigation: documented; `hydrate=False` is a niche non-hydrating mode.
