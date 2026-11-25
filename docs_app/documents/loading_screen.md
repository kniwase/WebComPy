---
title: Loading Screen
description: Configure the boot-time loading experience — presentation modes, interaction policies, staged progress, dormant wake-up timing, custom templates, and accessibility.
---

# Loading Screen

While the PyScript/Pyodide runtime downloads wheels and boots in the browser, WebComPy renders a framework-owned loading experience before your application hydrates. By default, pre-rendered pages keep their content readable beneath a slim top progress bar while gently waking up once hydration settles; blank shells fall back to a centered spinner overlay. Everything is configurable through `WebComPyAppConfig.loading`.

## Presentation modes and configuration

Configure `loading` on `WebComPyAppConfig` when instantiating `WebComPyApp`:

```python
from webcompy.app import WebComPyApp, WebComPyAppConfig

app = WebComPyApp(
    root_component=AppRoot,
    config=WebComPyAppConfig(
        loading={
            "mode": "auto",            # "auto" | "overlay" | "content"
            "interaction": "block",    # "block" | "inert" | "passthrough" (content mode)
            "stages": True,            # show staged boot progress labels
            "dormant": True,           # muted pre-rendered UI + wake-up transition
            "messages": {
                "runtime_download": "Loading Python runtime…",
            },
            "template": None,          # preset name, HTML string, or relative file path
            "reveal_delay_ms": 350,    # grace period (ms, max 10000) before chrome appears
            "fade_out_ms": 250,        # fade-out duration (ms, max 10000) on completion
            "timeout_seconds": 30,     # stall watchdog (seconds, max 3600; 0 disables)
        }
    ),
)
```

All keys are optional—config construction raises `ValueError` or `TypeError` immediately if unknown keys, out-of-range durations, or unrecognized `messages` stage keys are passed.

### Mode resolution

Resolution happens at HTML generation time:

- **`"auto"` (default)**: resolves to `"content"` when the page ships pre-rendered content (dev server, prod server, and `webcompy generate` always pre-render) and `"overlay"` otherwise.
- **`"content"`**: keeps pre-rendered HTML visible while showing a top progress bar and compact bottom-left status label.
- **`"overlay"`**: displays a centered spinner on a translucent full-viewport backdrop.

## Grace period, interaction policies, and wake-up

WebComPy suppresses all visual chrome (progress bar, spinner, status label, dormant muting) during the initial **`reveal_delay_ms` grace period (default `350 ms`)**. If cached assets finish booting within 350 ms, no loading indicator is ever painted.

In `"content"` mode, choose how user input behaves until hydration finishes:

| `interaction` | Behavior during boot | Best for |
|---|---|---|
| `"block"` (default) | Transparent full-screen blocker intercepts pointer clicks while scrolling and reading remain unobstructed | Most SSR/SSG apps wanting read-while-booting without broken dead clicks |
| `"inert"` | Adds the `inert` attribute to the mount container (`#webcompy-app`), blocking pointer events, keyboard focus, and selection | Strict apps preventing focus inside controls before Python handlers attach |
| `"passthrough"` | Intercepts nothing; native `<a href="...">` links navigate as regular MPA requests | Content-first pages relying solely on `dormant` visual cues until JS/Python wakes |

The mount container carries `aria-busy="true"` during boot and loses both `aria-busy` and any interaction lock as soon as initial hydration and its render-task drain (`await_pending(only_render=True)`) finish.

### Dormant treatment and fade-out

When `dormant=True` (default) in `"content"` mode and boot runs past the grace period:

- Pre-rendered application content gently mutes via `--wc-dormant-opacity` (default `0.9`) and `--wc-dormant-saturation` (default `0.85`).
- Upon completion, content transitions smoothly back to full vibrancy (`0.3s ease`, completing cleanly even when `fade_out_ms` is shorter) while `#webcompy-loading` fades out over `fade_out_ms` (default **`250 ms`**) and detaches from the DOM. Set `dormant=False` to keep pre-rendered content at full contrast throughout boot.

## Staged progress and stall watchdog

With `stages=True` (default), PyScript lifecycle events (`py:progress` and `py:ready`) drive five fixed stages, capped at monotonic progress ceilings until first render completes at 100%:

| Stage key | Default label | Progress ceiling |
|---|---|---|
| `runtime_prepare` | `Preparing Python runtime…` | `35%` |
| `runtime_download` | `Downloading Python runtime…` | `60%` |
| `packages` | `Installing packages…` | `85%` |
| `runtime_ready` | `Runtime ready…` | `93%` |
| `app_start` | `Starting app…` | `97%` |

Only these five keys are valid in `messages={...}` (for localization or custom copy). Micropip package log lines emitted during `packages` appear in the visual-only sub-status line (`aria-hidden="true"`). Setting `stages=False` omits stage labels and switches the bar to pure smooth CSS `transform` trickle capped below `97%` until first render reaches `100%`.

If no boot progress event (or `py:ready` signal) arrives within **`timeout_seconds` (default `30 s`)**, the stall watchdog reveals the timeout message (`"Taking longer than usual…"`) with a reload button. Every progress event and `py:ready` resets the timer; setting `timeout_seconds=0` disables the watchdog.

## Custom templates and the toolkit contract

Replace the default loading markup using `"template"`:

- **Built-in preset names**: `"overlay"`, `"bar"`, or `"splash"`.
- **Inline HTML string** (starts with `<`) or **package-relative HTML file path** (raises `WebComPyException` at build time if missing).

Every custom template **must** contain **exactly one** element with `id="webcompy-loading"`; HTML generation fails otherwise. Inside `#webcompy-loading`, WebComPy automatically drives up to five optional hooks when present (missing hooks are silently ignored):

| Hook attribute | Driven behavior |
|---|---|
| `[data-wc-status]` | Receives current stage label text |
| `[data-wc-substatus]` | Receives package-install detail lines (`aria-hidden="true"`) |
| `[data-wc-bar]` | Receives `--wc-progress` custom property as a unitless `0`–`1` fraction (e.g. `transform: scaleX(var(--wc-progress))`) |
| `[data-wc-timeout]` | Hidden until stall watchdog trips (`hidden` attribute optional on initial markup) |
| `[data-wc-reload]` | Clicking triggers page reload |

Optional mechanic attributes on `#webcompy-loading` (`data-wc-fade` in ms, `data-wc-mode`) override generated defaults when authored explicitly; otherwise WebComPy injects `role="status"`, `data-wc-mode`, `data-wc-interaction` (`content` mode), `data-wc-fade`, and `--wc-delay` / `--wc-fade` inline style variables. Framework base styles always emit *before* `#webcompy-loading`, so `<style>` blocks in your template override framework defaults cleanly.

## Theme tokens, accessibility, and CSP

Default styles read your active theme (`data-theme`, theme signal, or OS `prefers-color-scheme`) and can be customized via CSS custom properties: `--wc-accent`, `--wc-backdrop`, `--wc-ring`, `--wc-fg`, `--wc-dormant-opacity`, and `--wc-dormant-saturation`.

Accessibility & motion contracts:

- `#webcompy-loading` carries `role="status"` and announces stage changes via `aria-live="polite"` (while package sub-status stays `aria-hidden="true"` so screen readers aren't flooded).
- Under `prefers-reduced-motion: reduce`, spinner rotation, bar trickle, fade-out, and dormant wake-up transitions are disabled while preserving the `reveal_delay_ms` grace period and live stage announcements.

## Pitfalls

- **Authoring `style="..."` directly on custom `#webcompy-loading`**: When your custom element already declares its own `style` attribute, WebComPy preserves it untouched instead of injecting `--wc-delay` and `--wc-fade`. Add `data-wc-fade="..."` explicitly in that case so the removal fade duration stays configuration-driven.
- **`id="webcompy-loading"` validation**: Template validation scans HTML markup directly—mentioning `id="webcompy-loading"` multiple times or inside comments/inline scripts fails the exact-once check.
- **Strict Content-Security-Policy (CSP)**: The loading controller runs as an inline classic `<script>` generated with the page. Strict CSP deployments must allow inline scripts via nonce/hash or permit inline execution for that block.

## Next steps

- See how pre-rendered HTML and the render-task drain lead up to loading teardown in [SSR & SSG](/documents/advanced/ssr-and-ssg) and [Async Rendering & Boundaries](/documents/advanced/async-rendering-and-boundaries).
- Understand state transfer happening immediately before `#webcompy-loading` disappears in [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).
- Explore CSS variables and cascade rules used by loading and theme tokens in [Styling Deep Dive](/documents/advanced/styling-deep-dive).
- Full API: [App & Components API](/documents/api/app-and-components).
