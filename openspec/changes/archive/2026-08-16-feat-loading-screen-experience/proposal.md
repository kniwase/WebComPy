# Proposal: Loading Screen Experience

## Why

WebComPy apps boot a WASM Python runtime (Pyodide via PyScript), which takes from ~1s (cached) to 10-30s (cold) — the same weight class as Blazor WebAssembly or JupyterLite. The current loading screen is a dated 100px "W3Schools-style" border spinner on a 50% black veil, shown instantly even on fast cached boots, removed with a hard cut, and offering zero progress information during long cold boots. Perceived-performance research (NN/g; Drexel) and the WASM-framework peer group both point the same way: long, variable waits need visible progress, pre-rendered content should stay readable, and boot completion should feel like the app "waking up" rather than a wall being lifted.

## What Changes

- **Refined default visual**: compact spinner, theme-aware colors, 350ms grace period before any loading chrome appears (cached boots show nothing), 250ms fade-out on removal instead of instant `remove()`.
- **Content-first presentation**: pre-rendered pages remain fully readable during boot. The full-screen dark veil is replaced by a slim top progress bar plus a small status label. A "dormant" treatment (slightly muted content) signals that the page is not yet interactive and transitions to full vibrancy on ready — the "wake-up" moment.
- **Staged progress** driven by PyScript `py:progress` events (verified against the pinned 2026.3.1 release bundle): runtime prepare → runtime download → package install (incl. micropip sub-status lines) → runtime ready → app start. Hybrid progress bar: stage-completion ceilings + atan-style trickle; reaches 100% only on actual completion.
- **Interaction policy during boot**: configurable `block` (default; transparent full-screen click blocker, reading/scrolling preserved), `inert`, or `passthrough`.
- **Failure honesty**: a watchdog shows a "taking longer than usual" message with a reload affordance when progress stalls (default 30s), replacing today's infinite-spinner failure mode.
- **Developer configurability**: new `WebComPyAppConfig.loading` dict (following the `theme` dict precedent) controlling mode (`auto`/`overlay`/`content`), interaction policy, stage labels (i18n by full message override), timings, and custom templates. A documented toolkit contract (required `#webcompy-loading` ID, `[data-wc-status]` / `[data-wc-bar]` hooks, `--wc-*` CSS custom properties, preset templates) lets developers ship fully custom branded splash screens while the framework keeps driving progress plumbing. Custom templates are validated at HTML generation time.
- **Accessibility**: `role="status"` + `aria-live="polite"` for stage messages, `aria-busy` on the mount element during boot, all animations disabled under `prefers-reduced-motion`.

## Capabilities

### New Capabilities

- `loading-screen`: Boot-time loading experience — presentation modes, interaction policies, staged progress via `py:progress`, grace period and fade-out timing, dormant/wake-up treatment, timeout watchdog, accessibility behavior, and the custom-template toolkit contract.

### Modified Capabilities

- `app`: The "loading indicator removed on first render" requirement changes — removal becomes a sequenced transition (fade-out, dormant wake-up, `aria-busy` clearing) instead of an instantaneous `remove()`.
- `app-config`: `WebComPyAppConfig` gains a validated `loading` dict field with normalization, following the existing `theme` field pattern.
- `cli`: Generated HTML gains the loading controller inline script, data-attribute serialization of loading config onto `#webcompy-loading`, and build-time validation of custom templates.
- `demo-iframe-isolation`: The demo iframe loading screen visuals are synchronized with the refined default (the `#webcompy-loading` ID contract and auto-removal behavior are unchanged).

## Known Issues Addressed

None — this change does not resolve any entry from the project's known-issues list.

## Non-goals

- **Event replay** (capturing clicks during boot and re-dispatching after hydration) — high complexity, marginal benefit.
- **Byte-accurate download progress** for the Pyodide WASM payload — no official PyScript/Pyodide API exists; stage-based progress with trickle is the honest approximation.
- **Worker-mode PyScript boot** changes — WebComPy runs on the main thread; nothing about that changes.
- **Hydration mechanics** — node adoption, signal transfer, and render pipeline are untouched; only the loading chrome around them changes.
- **Per-route loading customization** — the `loading` config is app-global.
- **Default framework branding** — no WebComPy logo in the default experience; branding is the custom-template use case.

## Impact

- **Code**:
  - `packages/webcompy/src/webcompy/app/_config.py` — new `loading` field + `_normalize_loading_config()` validation.
  - `packages/webcompy-server/src/webcompy_server/_html.py` — `_Loadscreen` redesign, loading controller inline script, config → data-attribute serialization, template resolution/validation.
  - `packages/webcompy/src/webcompy/app/_root_component.py` — sequenced removal (fade-out, dormant wake-up, `aria-busy` clearing).
  - `docs_app/static/_demos/standard.html` — sync static demo iframe copy with refined default.
- **Specs**: new `loading-screen` spec; deltas for `app`, `app-config`, `cli`, `demo-iframe-isolation`. `AGENTS.md` File→Spec mapping and Current Specs list updated accordingly.
- **Tests**: unit tests for config validation and HTML generation; new E2E coverage for staged status, fade-out, and modes. Existing E2E (`wait_for_selector("#webcompy-loading", state="hidden")`) remains compatible — opacity 0 still counts as visible to Playwright until actual removal.
- **APIs**: additive only — `WebComPyAppConfig.loading` is a new optional field. No breaking changes; the `#webcompy-loading` DOM contract (ID, removal trigger) is preserved.
- **Docs**: new documentation page covering the `loading` config and the custom-template toolkit contract.
