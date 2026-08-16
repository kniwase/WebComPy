# Tasks: Loading Screen Experience

## 1. Configuration Foundation

- [ ] 1.1 Add `loading: dict | None` field to `WebComPyAppConfig` with `_normalize_loading_config()` in `__post_init__`, following the `theme` precedent: keys `mode`, `interaction`, `stages`, `messages`, `template`, `reveal_delay_ms`, `fade_out_ms`, `timeout_seconds` with documented defaults and `TypeError`/`ValueError` validation (including unknown `messages` stage keys)
- [ ] 1.2 Unit tests for loading config normalization: defaults when omitted/None, valid partial dicts, invalid key, invalid mode, invalid value type, unknown stage key in messages

## 2. Phase 1 — Refined Default Visual & Removal Transition

- [ ] 2.1 Redesign `_Loadscreen` in `webcompy_server/_html.py`: compact spinner, theme-aware colors keyed off `html[data-theme]` with `light-dark()` fallback, refined translucent backdrop, `--wc-*` CSS custom properties surface
- [ ] 2.2 Implement the grace period in the loading stylesheet: all chrome starts at `opacity: 0` and is revealed by a delayed forwards-fill animation driven by `reveal_delay_ms`
- [ ] 2.3 Serialize normalized loading config onto `#webcompy-loading` as `data-wc-*` attributes in generated HTML (mode, interaction, reveal delay, fade-out, timeout)
- [ ] 2.4 Replace instantaneous `loading_el.remove()` in `AppDocumentRoot._render()` with the sequenced removal: add fade class, await `fade_out_ms`, then remove; read attributes with framework defaults when absent; no-op silently when the element does not exist
- [ ] 2.5 Sync the static demo iframe copy `docs_app/static/_demos/standard.html` with the refined overlay visual, preserving the `#webcompy-loading` contract
- [ ] 2.6 Unit tests: generated HTML contains the new markup, inline styles, and `data-wc-*` attributes; removal honors a custom fade duration attribute
- [ ] 2.7 E2E: assert the fade class is present before the element leaves the DOM; confirm all existing `#webcompy-loading` hidden-wait tests still pass unmodified

## 3. Phase 2 — Loading Controller: Staged Progress, Bar, Watchdog

- [ ] 3.1 Measure real boot phases with `profile=True` instrumentation (cold vs cached) to calibrate stage ceilings, `reveal_delay_ms`, and `timeout_seconds` defaults; record findings in the change directory
- [ ] 3.2 Emit the inline loading controller `<script>` immediately after `#webcompy-loading` in generated HTML (classic script, dependency-free, `window` listeners for `py:progress`/`py:ready`)
- [ ] 3.3 Implement the stage mapping table (verified PyScript 2026.3.1 strings → `runtime_prepare`/`runtime_download`/`packages`/`runtime_ready`/`app_start`), default English labels, `messages` overrides, and micropip-line sub-status rendering
- [ ] 3.4 Implement the progress bar: stage-completion ceilings + atan-style trickle below the current ceiling, `transform: scaleX(var(--wc-progress))`, 100% only when removal begins
- [ ] 3.5 Implement the stall watchdog: timer reset on every progress event, `[data-wc-timeout]` reveal with reload affordance on expiry, `0` disables
- [ ] 3.6 Unit tests: generated controller contains the stage mapping and hook selectors; `stages: false` omits status markup; controller script is classic (not module)
- [ ] 3.7 E2E: with network throttling on Pyodide assets, assert stage labels appear in order; assert watchdog message appears when progress stalls; assert no watchdog after successful boot

## 4. Phase 3 — Modes, Interaction Policies, Dormant/Wake-up, Accessibility

- [ ] 4.1 Implement mode resolution at HTML generation: `auto` → `content` when prerendered content exists, else `overlay`; emit the overlay or content markup variant accordingly
- [ ] 4.2 Implement `content` mode chrome: slim top progress bar and corner status label markup/styles
- [ ] 4.3 Implement interaction policies: `block` (transparent full-screen interceptor), `inert` (attribute on the mount element), `passthrough` (no interception); all lifted on boot completion
- [ ] 4.4 Implement the dormant treatment: `wc-booting` body class in generated HTML, delayed dormant keyframes honoring the grace period, `--wc-dormant-opacity` and related CSS vars
- [ ] 4.5 Implement the wake-up sequence in the removal path (`wc-booting` → `wc-waking` → removed) and the mount element `aria-busy` lifecycle
- [ ] 4.6 Accessibility: `role="status"` on the loading element, `aria-live="polite"` on the stage label, `aria-hidden` sub-status, `prefers-reduced-motion` rules disabling all animations
- [ ] 4.7 Unit tests for mode/policy/dormant markup; E2E for `block` click interception, `passthrough` native link navigation, dormant visibility on slow boot, wake-up transition on completion

## 5. Phase 4 — Custom Templates, Presets, Toolkit

- [ ] 5.1 Implement template resolution: preset name, inline HTML string, or file path resolved relative to the app package directory
- [ ] 5.2 Implement generation-time template validation: exactly one `id="webcompy-loading"` (error), at least one documented hook (warning), missing file (error)
- [ ] 5.3 Implement the `overlay`, `bar`, and `splash` preset templates using the toolkit hooks
- [ ] 5.4 Add a docs_app documentation page for the toolkit contract: required ID, `[data-wc-*]` hooks, `--wc-*` CSS custom properties, mechanic attributes, CSP note for the inline controller
- [ ] 5.5 Unit tests for template resolution and validation paths; E2E with a custom template asserting hooks are driven

## 6. Documentation Sync and Housekeeping

- [ ] 6.1 Update `AGENTS.md`: File→Spec mapping entries for changed files, Current Specs list with the new `loading-screen` spec, and the Framework Invariants list if a new invariant emerges
- [ ] 6.2 Add a docs_app guide page for the `loading` configuration (all keys, defaults, examples per mode)
- [ ] 6.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
- [ ] 6.4 Run the full local CI gate: `ruff check`, `ruff format --check`, `pyright`, `pytest tests/`, `webcompy generate` on docs_app, and the relevant E2E groups
