# Design: Loading Screen Experience

## Context

See proposal.md — Why for motivation. Current state and verified constraints that shape this design:

- `_Loadscreen` (`webcompy_server/_html.py`) emits a static `#webcompy-loading` div + inline `<style>` as the first `<body>` child: 100px border spinner on `rgba(0,0,0,0.5)`, removed via instantaneous `loading_el.remove()` in `AppDocumentRoot._render()` (browser, `webcompy/app/_root_component.py`).
- Boot runs Pyodide on the **main thread** via `<script type="py">`; PyScript `core.js` is loaded as `type="module"` (deferred execution, after document parse).
- Both dev server (`_server.py`: `prerender=True`) and SSG (same serving app via ASGI transport) ship pre-rendered content beneath the loading element; `prerender=False` exists only in unit tests.
- **Verified against the pinned PyScript 2026.3.1 release bundle** (`core-BuLtL7jM.js`):
  - `py:progress` is dispatched on `window` (bare `dispatchEvent(new CustomEvent(\`${type}:progress\`, {detail}))`) — listeners must attach to `window`, not `document`.
  - Exact stage sequence for WebComPy's config (`packages` + `interpreter` + `lockFileURL`): `Loading Pyodide` → `Loading/Loaded Packages Graph` → `Loading/Loaded Storage` → `Loading interpreter` (the `loadPyodide()` call = WASM download + instantiate; the long pole) → `Loaded interpreter` → micropip install window (**each micropip `console.log` line is re-emitted as a `py:progress` event**; cache-miss only) → `Loaded Pyodide` → `py:ready` → app code runs → `py:done`/`py:all-done`.
  - The engine is fully `async`/`await` across network operations, so the event loop is free during all downloads; progress-driven DOM updates paint. WASM instantiation uses streaming compilation (mostly off-main-thread).
- CSS `transform`/`opacity` animations are compositor-driven and keep animating even if the main thread janks (why the current spinner survives Pyodide bootstrap).
- Playwright's visibility check treats `opacity: 0` as **visible** — a fade-out before removal is E2E-compatible with existing `state="hidden"` waits.

## Goals / Non-Goals

**Goals:**

- Boot experience honest about duration: staged progress with real PyScript events as the source of truth.
- Pre-rendered content stays readable during boot; non-interactivity is visually signaled, not hidden behind a veil.
- Fast cached boots show zero loading chrome (grace period); slow boots get rich feedback.
- Fully custom branded splash screens possible via a documented, validated toolkit contract.
- Zero breaking changes: `#webcompy-loading` ID contract, removal trigger, and E2E selectors preserved.

**Non-Goals:**

- Event replay of boot-time clicks; byte-accurate WASM download progress; worker-mode boot; hydration pipeline changes; per-route loading config; default framework branding (see proposal — Non-goals).

## Decisions

### Decision 1: Config lives in `WebComPyAppConfig.loading` (dict), serialized to data attributes

`WebComPyAppConfig` gains `loading: dict | None = None`, normalized in `__post_init__` by a `_normalize_loading_config()` — the exact pattern of the existing `theme` field (`_normalize_theme_config`). Keys:

| Key | Values | Default |
|---|---|---|
| `mode` | `"auto"` / `"overlay"` / `"content"` | `"auto"` |
| `interaction` | `"block"` / `"inert"` / `"passthrough"` | `"block"` |
| `stages` | `bool` | `True` |
| `messages` | `dict[stage_key, str]` | `{}` (English defaults) |
| `template` | preset name / HTML string / file path | `None` (framework default) |
| `reveal_delay_ms` | `int` | `350` |
| `fade_out_ms` | `int` | `250` |
| `timeout_seconds` | `int` (0 disables) | `30` |

The server-side HTML generator serializes the normalized config onto `#webcompy-loading` as `data-wc-*` attributes; browser-side removal code reads attributes with hardcoded defaults. **Rationale:** the generated HTML becomes self-contained — custom templates control their own fade/mode via attributes, and library usage without the CLI falls back to defaults automatically. Alternative considered: browser reads `app.config` directly — rejected because custom templates (developer-authored HTML) would silently diverge from Python-side config, and the DOM contract approach keeps the browser decoupled from config schema evolution.

`mode: "auto"` resolves at generation time: `content` when prerendered output exists (always, for dev + SSG — verified), `overlay` otherwise.

### Decision 2: Loading controller is an inline classic `<script>` immediately after the loading element

A small dependency-free inline script (the "loading controller") is emitted right after `#webcompy-loading` in `<body>`. Classic inline scripts execute during parsing; `type="module"` scripts (core.js) execute after parsing — so the controller is **guaranteed by the HTML spec** to register its `window.addEventListener("py:progress", ...)` before any event fires. No load-order flag day. Alternative considered: appending the listener via a head module — rejected (module execution timing + ordering vs. core.js is fragile). Precedent: the dev-mode reload `EventSource` script is already emitted inline the same way.

### Decision 3: Stage model maps verified `py:progress` strings to five stage keys

```
py:progress "Loading Pyodide"      → runtime_prepare   "Preparing Python runtime…"
py:progress "Loading interpreter"  → runtime_download  "Downloading Python runtime…"  ← long pole
py:progress "Loaded interpreter"   → packages          "Installing packages…"
py:progress "Loaded Pyodide"       → runtime_ready     "Runtime ready…"
window "py:ready"                  → app_start         "Starting app…"
```

Rules for the controller:

- Only exact known strings trigger stage transitions. `Packages Graph` / `Storage` / `files` / `fetch` / `JS modules` lines update nothing (or optionally the sub-status) — they are near-instant.
- On cache miss, micropip `console.log` lines arrive as arbitrary `py:progress` detail strings between `Loaded interpreter` and `Loaded Pyodide`; they are shown as **sub-status** (smaller secondary text) and never as stage transitions. They are visual-only (`aria-hidden`) to avoid aria-live chatter.
- The stage vocabulary is fixed; an unknown key in `messages` is a config validation error. Stage keys are decoupled from PyScript's English strings, so developer-supplied `messages` provide full i18n.

**Rationale:** grounded in the verified bundle behavior rather than documentation. Risk of PyScript version drift is contained: the mapping is a single table in the controller template, and version bumps are deliberate (gated by `PYSCRIPT_TO_PYODIDE`).

### Decision 4: Progress bar = stage ceilings + atan trickle, `transform: scaleX`

No byte-level progress API exists (verified Pyodide discussion). The bar therefore combines: (a) stage completion ceilings (e.g., prepare 35% → download 60% → packages 85% → ready 93% → app_start 97%, calibrated in `calibration.md`), and (b) a Nuxt-style `atan` trickle that approaches but never exceeds the current stage's ceiling while a stage is in flight. On each stage-start event the bar advances to the **previous** stage's ceiling (a floor, so completed stages are acknowledged) and the trickle then animates toward the new stage's ceiling — it never jumps all the way to the new ceiling at stage entry, which is what keeps motion visible during the interpreter download (the longest phase). The bar hits 100% only when the removal sequence begins. Rendering uses `transform: scaleX(var(--wc-progress))` — compositor-driven, so it animates smoothly even through main-thread jank. When `stages: false`, stage ceilings are not used at all: the bar progresses purely by trickle toward a fixed 97% ceiling and jumps to 100% only at completion. **Alternative considered:** pure trickle (no stages) — rejected; it lies during the WASM download, the one phase users most need honesty about.

### Decision 5: Grace period and dormant effect via CSS `animation-delay`, no JS

All loading chrome (bar, spinner, status, dormant content treatment) is suppressed for the first `reveal_delay_ms` (default 350ms) using pure CSS: elements start at `opacity: 0` and a delayed `forwards`-fill animation reveals them; if `#webcompy-loading` is removed before the delay elapses, nothing ever flashes. The dormant treatment uses the same trick: `body.wc-booting #webcompy-app { animation: wc-dormant-in 0.01s linear var(--wc-delay) forwards }` where the keyframe holds the muted end-state (`opacity: var(--wc-dormant-opacity, 0.9)`, slight desaturation). **Rationale:** works from first paint with zero JS, zero flash on cached boots, and removes the biggest "モッサリ" amplifier (spinner flash on fast loads).

### Decision 6: Dormant/wake-up lifecycle via body class tri-state

Generated HTML puts `class="wc-booting"` on `<body>` when dormant mode is active (content mode and `dormant: true`, the default; the `dormant` config key opts out, in which case no boot-state class is emitted and no wake-up runs). Wake-up sequence (browser removal path): `wc-booting` → `wc-waking` (transition to full vibrancy runs, ~300ms) → class removed. Scoping both dormant styles and the restore transition to these classes leaves **zero persistent side effects** on `#webcompy-app` (no permanent `transition` property that could hijack later app styling). The dormant/waking CSS rules are generated with the configured mount selector substituted for `#webcompy-app`, so custom-selector apps get the same treatment. Alternative considered: `body:has(> #webcompy-loading) #webcompy-app` self-removing selector — rejected for the wake-up transition: when `:has()` stops matching, values snap instantly unless a base transition exists, and a base transition on the app root is an unacceptable side effect.

### Decision 7: Interaction policies — `block` (default) / `inert` / `passthrough`

- `block`: in `content` mode the loading element remains full-screen fixed but transparent (no background). Clicks are caught; wheel scroll chains to the document; reading is unobstructed. Trade-off (documented in spec): text selection/copy is blocked during boot.
- `inert`: `inert` attribute on the mount element — blocks pointer, keyboard focus, and selection; correctly announced by AT. Strongest honesty, also blocks copying.
- `passthrough`: no blocker at all. Links work via MPA fallback (RouterLink renders real `<a href>`; history-mode SSG targets exist as static pages), buttons stay dead — honest only because the dormant treatment signals "not yet alive". Recommended for content sites.

**Rejected:** event capture + replay after hydration (complexity, surprising late navigations); selective passthrough for anchors only (inconsistent — dead buttons next to working links reads as broken, not degraded).

### Decision 8: Removal becomes a sequenced transition in `AppDocumentRoot._render()`

Browser-side, replacing `loading_el.remove()`:

1. Read `data-wc-*` attributes (fade duration, dormant on/off) with defaults.
2. Mark `py:ready`-equivalent completion → bar to 100% (controller exposed hook or direct class).
3. Add fade class (`opacity → 0` transition, `fade_out_ms`).
4. Swap body class `wc-booting` → `wc-waking`; clear `aria-busy` on the mount element.
5. After the fade duration (`await asyncio.sleep(fade_ms / 1000)` — `_render` is already async), remove the element. If the wake-up transition (fixed 300ms) is still running, wait for the remainder before removing the `wc-waking` class, so a short `fade_out_ms` never truncates the wake-up.

E2E compatibility: `opacity: 0` remains Playwright-"visible" until actual `remove()`, so all `state="hidden"` waits keep passing (just ~250ms later). In the server/SSG render path nothing changes (`_Loadscreen` is only markup).

### Decision 9: Timeout watchdog in the controller

Every `py:progress` resets a timer (`timeout_seconds`, default 30, 0 disables). On expiry the controller reveals a `[data-wc-timeout]` element: "Taking longer than usual…" + reload button. This converts the infinite-spinner failure mode (e.g., corporate firewalls blocking WASM — a documented Blazor-community pain) into honest feedback with an escape hatch. It is deliberately a **stall detector**, not an error classifier — PyScript error taxonomy is not stable enough to parse.

### Decision 10: Theme-aware colors keyed off theme tokens, `light-dark()` fallback

The theme system renders the active theme via token overrides on `:root` — the `ThemeManager` reactive style (theme signal) or the `tokens.css` `[data-theme]` / `prefers-color-scheme` blocks — rather than a `data-theme` attribute. Loading CSS therefore keys its default surface/foreground/accent colors off the theme design tokens (`--color-*`) with `light-dark()` as the final fallback, so the loading screen follows whichever mechanism the theme system uses (theme signal, `data-theme` attribute, or OS preference). All colors are overridable via `--wc-*` custom properties, which is also the toolkit theming surface.

### Decision 11: Toolkit contract with build-time validation

Public contract for custom templates (`template` config: preset name, HTML string, or file path resolved relative to the app package):

- **Required:** exactly one element with `id="webcompy-loading"` — validated at HTML generation; missing → build error. This ID is the sole hard dependency of removal logic and E2E.
- **Driven hooks (optional):** `[data-wc-status]` (stage label target), `[data-wc-substatus]` (micropip lines), `[data-wc-bar]` (receives `--wc-progress: 0–100`), `[data-wc-timeout]` (hidden until watchdog trips). Missing hooks are no-ops; the controller always runs.
- **CSS custom properties:** `--wc-accent`, `--wc-backdrop`, `--wc-fg`, `--wc-dormant-opacity`, `--wc-progress`.
- **Presets:** `"overlay"` (refined centered spinner — the `overlay` mode default), `"bar"` (slim top bar — the `content` mode default), `"splash"` (centered brand block).
- Templates may set their own `data-wc-fade` / `data-wc-mode` attributes to override mechanics. Generation injects the resolved `data-wc-*` attributes and `--wc-delay`/`--wc-fade` style variables onto the template's `#webcompy-loading` element when the template does not set them, so the generated HTML stays self-contained.

**Rationale:** the framework owns behavior (progress, timeout, removal); developers own appearance. Validation catches the one catastrophic failure (missing ID) at build time, not in production.

### Decision 12: Accessibility built into the default markup

`#webcompy-loading` carries `role="status"`; the stage label is `aria-live="polite"`; the mount element gets `aria-busy="true"` until ready; `@media (prefers-reduced-motion: reduce)` disables rotation, fade, trickle, and dormant transitions (a static "Loading…" state remains — the grace period is kept since it prevents flash, not motion).

## Risks / Trade-offs

- **[Main-thread WASM instantiation jank freezes status text briefly]** → Bar/spinner animation is compositor-driven (`transform`) and keeps moving; text jank is sub-second and acceptable. Verified: engine awaits make all download phases paintable.
- **[PyScript version bump changes `py:progress` strings]** → Mapping isolated in one controller template table; version bumps are deliberate and gated by `PYSCRIPT_TO_PYODIDE`; unit test asserts the generated controller contains the mapping for the pinned version.
- **[`block` policy prevents text selection during boot]** → Documented trade-off; `passthrough` opt-in for content sites where copying during boot matters.
- **[Inline controller script vs. strict CSP]** → Precedent exists (dev reload script, conditional plugin scripts); documentation notes the CSP hash requirement.
- **[Custom template authors omit all hooks]** → Build-time warning (not error) when no known hook is present; behavior degrades to a static splash that still fades and removes correctly.
- **[Dormant desaturation could hurt readability if tuned aggressively]** → Default is subtle (`opacity 0.9`, mild desaturate); both exposed as CSS vars.
- **[`:has()` avoided deliberately; `inert` used only for opt-in policy]** → Baseline-2023 features only where opted in; default path needs neither.

## Migration Plan

No migration. The change is additive (`loading` config optional) and visually transparent. Generated HTML gains new markup/attributes; the only behavioral deltas are later removal (+fade) and suppressed chrome on sub-350ms boots — both universally desirable. Demo iframe static copy (`docs_app/static/_demos/standard.html`) is updated in the same change to keep visuals consistent.

## Open Questions

- Calibration of `reveal_delay_ms` (350ms) and `timeout_seconds` (30s) defaults — to be measured with the existing `profile=True` boot-phase instrumentation during implementation (Phase 2). Adjusting these numbers changes neither specs nor task breakdown.
- Sub-status truncation policy for long micropip lines (cosmetic; decided at implementation).
