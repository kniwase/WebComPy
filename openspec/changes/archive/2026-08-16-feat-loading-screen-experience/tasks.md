# Tasks: Loading Screen Experience

## 1. Configuration Foundation

- [x] 1.1 Add `loading: dict | None` field to `WebComPyAppConfig` with `_normalize_loading_config()` in `__post_init__`, following the `theme` precedent: keys `mode`, `interaction`, `stages`, `dormant`, `messages`, `template`, `reveal_delay_ms`, `fade_out_ms`, `timeout_seconds` with documented defaults and `TypeError`/`ValueError` validation (including unknown `messages` stage keys)
- [x] 1.2 Unit tests for loading config normalization: defaults when omitted/None, valid partial dicts, invalid key, invalid mode, invalid value type, unknown stage key in messages

## 2. Phase 1 — Refined Default Visual & Removal Transition

- [x] 2.1 Redesign `_Loadscreen` in `webcompy_server/_html.py`: compact spinner, theme-aware colors keyed off `html[data-theme]` with `light-dark()` fallback, refined translucent backdrop, `--wc-*` CSS custom properties surface
- [x] 2.2 Implement the grace period in the loading stylesheet: all chrome starts at `opacity: 0` and is revealed by a delayed forwards-fill animation driven by `reveal_delay_ms`
- [x] 2.3 Serialize normalized loading config onto `#webcompy-loading` as `data-wc-*` attributes in generated HTML (mode, interaction, reveal delay, fade-out, timeout)
- [x] 2.4 Replace instantaneous `loading_el.remove()` in `AppDocumentRoot._render()` with the sequenced removal: add fade class, await `fade_out_ms`, then remove; read attributes with framework defaults when absent; no-op silently when the element does not exist
- [x] 2.5 Sync the static demo iframe copy `docs_app/static/_demos/standard.html` with the refined overlay visual, preserving the `#webcompy-loading` contract
- [x] 2.6 Unit tests: generated HTML contains the new markup, inline styles, and `data-wc-*` attributes; removal honors a custom fade duration attribute
- [x] 2.7 E2E: assert the fade class is present before the element leaves the DOM; confirm all existing `#webcompy-loading` hidden-wait tests still pass unmodified

## 3. Phase 2 — Loading Controller: Staged Progress, Bar, Watchdog

- [x] 3.1 Measure real boot phases with `profile=True` instrumentation (cold vs cached) to calibrate stage ceilings, `reveal_delay_ms`, and `timeout_seconds` defaults; record findings in the change directory
- [x] 3.2 Emit the inline loading controller `<script>` immediately after `#webcompy-loading` in generated HTML (classic script, dependency-free, `window` listeners for `py:progress`/`py:ready`)
- [x] 3.3 Implement the stage mapping table (verified PyScript 2026.3.1 strings → `runtime_prepare`/`runtime_download`/`packages`/`runtime_ready`/`app_start`), default English labels, `messages` overrides, and micropip-line sub-status rendering
- [x] 3.4 Implement the progress bar: stage-completion ceilings + atan-style trickle below the current ceiling, `transform: scaleX(var(--wc-progress))`, 100% only when removal begins; when `stages` is false, the bar progresses by pure trickle toward a fixed 97% ceiling without stage jumps
- [x] 3.5 Implement the stall watchdog: timer reset on every progress event, `[data-wc-timeout]` reveal with reload affordance on expiry, `0` disables
- [x] 3.6 Unit tests: generated controller contains the stage mapping and hook selectors; `stages: false` omits status markup; controller script is classic (not module)
- [x] 3.7 E2E: with network throttling on Pyodide assets, assert stage labels appear in order; assert watchdog message appears when progress stalls; assert no watchdog after successful boot

## 4. Phase 3 — Modes, Interaction Policies, Dormant/Wake-up, Accessibility

- [x] 4.1 Implement mode resolution at HTML generation: `auto` → `content` when prerendered content exists, else `overlay`; emit the overlay or content markup variant accordingly
- [x] 4.2 Implement `content` mode chrome: slim top progress bar and corner status label markup/styles
- [x] 4.3 Implement interaction policies: `block` (transparent full-screen interceptor), `inert` (attribute on the mount element), `passthrough` (no interception); all lifted on boot completion
- [x] 4.4 Implement the dormant treatment: `wc-booting` body class emitted only when `dormant` is enabled (content mode, default), delayed dormant keyframes honoring the grace period, `--wc-dormant-opacity` and related CSS vars
- [x] 4.5 Implement the wake-up sequence in the removal path (`wc-booting` → `wc-waking` → removed) and the mount element `aria-busy` lifecycle
- [x] 4.6 Accessibility: `role="status"` on the loading element, `aria-live="polite"` on the stage label, `aria-hidden` sub-status, `prefers-reduced-motion` rules disabling all animations
- [x] 4.7 Unit tests for mode/policy/dormant markup; E2E for `block` click interception, `passthrough` native link navigation, dormant visibility on slow boot, wake-up transition on completion

## 5. Phase 4 — Custom Templates, Presets, Toolkit

- [x] 5.1 Implement template resolution: preset name, inline HTML string, or file path resolved relative to the app package directory
- [x] 5.2 Implement generation-time template validation: exactly one `id="webcompy-loading"` (error), at least one documented hook (warning), missing file (error)
- [x] 5.3 Implement the `overlay`, `bar`, and `splash` preset templates using the toolkit hooks
- [x] 5.4 Add a docs_app documentation page for the toolkit contract: required ID, `[data-wc-*]` hooks, `--wc-*` CSS custom properties, mechanic attributes, CSP note for the inline controller
- [x] 5.5 Unit tests for template resolution and validation paths; E2E with a custom template asserting hooks are driven

## 6. Documentation Sync and Housekeeping

- [x] 6.1 Update `AGENTS.md`: File→Spec mapping entries for changed files, Current Specs list with the new `loading-screen` spec, and the Framework Invariants list if a new invariant emerges
- [x] 6.2 Add a docs_app guide page for the `loading` configuration (all keys, defaults, examples per mode)
- [x] 6.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
- [x] 6.4 Run the full local CI gate: `ruff check`, `ruff format --check`, `pyright`, `pytest tests/`, `webcompy generate` on docs_app, and the relevant E2E groups

## 7. Review Fixes

- [x] 7.1 Fix the loading controller progress semantics: track the trickle ceiling in a numeric variable and advance the bar to the previous stage's ceiling on stage entry instead of jumping to the current ceiling (repairs the `stage` key-vs-index defect and restores smooth motion toward the in-flight stage's ceiling); harden the trickle loop with an `isConnected` guard
- [x] 7.2 Add E2E regression coverage: bar trickles during the interpreter download stage; `passthrough` works with custom templates
- [x] 7.3 Inject resolved loading attributes (`data-wc-mode`, `data-wc-interaction` in content mode, `data-wc-fade`, and `--wc-delay`/`--wc-fade` style variables) into custom templates at generation time, preserving template-authored attributes
- [x] 7.4 Validate `messages` values are strings and copy the `messages` default to avoid shared mutable state
- [x] 7.5 Wire `--wc-fg`/`--wc-ring`/`--wc-accent` CSS custom properties into the base stylesheet and extend the dark-theme rules
- [x] 7.6 Add unit tests for attribute injection, message value validation, CSS variable wiring, and the hook-less template warning

## 8. Second Review Fixes

- [x] 8.1 Embed resolved loading timing into the generated CSS fallbacks so the dormant treatment honors `reveal_delay_ms` and the fade transition honors `fade_out_ms` (`_loading_base_css(loading)`); default output unchanged
- [x] 8.2 Sync `--wc-fade` from the `data-wc-fade` attribute in the controller so template-authored fade attributes always match the CSS transition duration
- [x] 8.3 Restrict sub-status rendering to the packages window (`Loaded interpreter` → `Loaded Pyodide`) via a `showSub` flag
- [x] 8.4 Stop the trickle loop under `prefers-reduced-motion` (`matchMedia` gate); stage-driven bar updates remain
- [x] 8.5 Guard the watchdog against revealing after boot completion (`data-wc-complete` check in the timer callback)
- [x] 8.6 Exempt `aria-busy`/`inert` from the mount-element attribute sanitization so the removal sequence remains the sole releaser; extend E2E with `aria-busy` assertions
- [x] 8.7 Bound `reveal_delay_ms`/`fade_out_ms` (0–10000) and `timeout_seconds` (0–3600) and document the ranges in the app-config delta spec
- [x] 8.8 Remove the dead `data-wc-selector` attribute and copy `messages` in `_resolve_loading_config`
- [x] 8.9 Align the cli delta spec serialization wording with the implementation (style variables + controller configuration)

## 9. Third Review Fixes

- [x] 9.1 Scope the dormant/wake-up CSS rules to the configured mount selector (`_loading_base_css(loading, selector)` substitutes `#webcompy-app`); add unit tests for custom-selector CSS emission
- [x] 9.2 Complete the wake-up transition regardless of `fade_out_ms`: wait for the fixed 300ms transition remainder before removing the `wc-waking` class (`_loading_wake_remaining_ms`); add unit tests for the timing helper
- [x] 9.3 Drop `pointer-events: auto` from the `.wc-status` rule so `passthrough` mode leaves the status label non-interceptive (`.wc-timeout` keeps it for the reload button)
- [x] 9.4 Replace the bare marker assert with a `WebComPyException` naming the missing contract marker
- [x] 9.5 Document that a template-authored `style` attribute skips `--wc-delay`/`--wc-fade` injection in the loading screen docs page
- [x] 9.6 Extend the loading-screen delta spec with the custom-mount-selector dormant scenario and the wake-up completion guarantee; record the changes in design.md Decisions 6/8
- [x] 9.7 Run the local CI gate: `ruff check`, `ruff format --check`, `pyright`, `pytest tests/`, `webcompy generate` on docs_app, and the `bootstrap-static` E2E group

## 10. Fourth Review Fixes

- [x] 10.1 Respect quoted attribute values when locating the tag end for loading template attribute injection (`_find_tag_end`); prevents duplicate attribute injection when an attribute value between the `id` and mechanic attributes contains `>`; add unit tests for `data-wc-fade` and `style` preservation
- [x] 10.2 Bound the browser-side fade duration read from `data-wc-fade` to the configured maximum (10000ms)
- [x] 10.3 Hide `[data-wc-timeout]` elements on controller init so templates without an initial `hidden` attribute behave per contract; document the behavior in the loading screen docs page
- [x] 10.4 Fail the loading server readiness wait when it exhausts its attempts (E2E infrastructure)
- [x] 10.5 Align loading-screen delta spec scenarios with the implementation: `WebComPyAppConfig(loading={})` normalization wording and the `data-wc-reload` hook enumeration (app-config, cli, loading-screen)
- [x] 10.6 Run the local CI gate: `ruff check`, `ruff format --check`, `pyright`, `pytest tests/`, `webcompy generate` on docs_app, and the `bootstrap-static` + `docs-documents` E2E groups
