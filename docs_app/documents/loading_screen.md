---
title: Loading Screen
description: Configure the boot-time loading experience — presentation modes, interaction policies, staged progress, custom templates, and the toolkit contract.
---

# Loading Screen

Every WebComPy page shows a loading screen while the PyScript/Pyodide runtime downloads and initializes in the browser. The framework default is tuned for perceived performance: pre-rendered content stays readable, a slim top bar shows staged progress, and the page visually "wakes up" when the app is ready. Everything is configurable through `WebComPyAppConfig.loading`.

## Configuration

```python
from webcompy.app import WebComPyApp, WebComPyAppConfig

app = WebComPyApp(
    root_component=AppRoot,
    config=WebComPyAppConfig(
        loading={
            "mode": "auto",            # auto | overlay | content
            "interaction": "block",    # block | inert | passthrough (content mode)
            "stages": True,            # show staged status labels
            "dormant": True,           # muted content + wake-up transition
            "messages": {
                "runtime_download": "Loading Python runtime…",
            },
            "template": None,          # preset name, HTML string, or file path
            "reveal_delay_ms": 350,    # grace period before any chrome appears
            "fade_out_ms": 250,        # fade-out duration on boot completion
            "timeout_seconds": 30,     # stall watchdog (0 disables)
        }
    ),
)
```

All keys are optional. Unknown keys, invalid values, and unknown `messages` stage keys are rejected at config construction time.

### Modes

- `auto` (default) — `content` when the page ships pre-rendered content (dev server and SSG always do), `overlay` otherwise.
- `content` — the page stays fully readable; a slim top progress bar and a small bottom-left status label communicate boot progress. A click-blocker prevents interaction until the app is live.
- `overlay` — a centered spinner on a translucent backdrop (used when there is no pre-rendered content).

### Interaction policies (content mode)

- `block` (default) — a transparent full-screen element intercepts clicks during boot; scrolling and reading stay possible.
- `inert` — the mount element carries the `inert` attribute, additionally blocking keyboard focus and selection.
- `passthrough` — nothing is intercepted; links navigate natively (MPA fallback). The dormant treatment is what honestly signals "not interactive yet".

### Staged progress

`stages: true` shows the current boot phase: `Preparing Python runtime…` → `Downloading Python runtime…` → `Installing packages…` → `Runtime ready…` → `Starting app…`. Labels are driven by PyScript's `py:progress` events and can be localized via `messages` (stage keys are fixed; see the `loading-screen` spec). With `stages: false`, the status label is omitted and the progress bar becomes a pure trickle without stage jumps.

### Stall watchdog

If no boot progress event arrives within `timeout_seconds`, a "Taking longer than usual…" message with a reload button appears. Set `0` to disable.

## Custom templates and the toolkit contract

`template` accepts a preset name (`"overlay"`, `"bar"`, `"splash"`), an inline HTML string, or a path to an HTML file resolved relative to the app package directory. A custom template must contain exactly one element with `id="webcompy-loading"` — generation fails with a clear error otherwise. Validation is a lightweight markup scan, so a template that merely mentions the contract ID inside a comment or script may fail the check.

The framework drives documented hooks inside the loading element when present; missing hooks are no-ops:

| Hook | Driven by |
|---|---|
| `[data-wc-status]` | current stage label |
| `[data-wc-substatus]` | package-install detail lines (visual only, `aria-hidden`) |
| `[data-wc-bar]` | `--wc-progress` custom property as a unitless 0–1 fraction (e.g. `transform: scaleX(var(--wc-progress))`) |
| `[data-wc-timeout]` | revealed by the stall watchdog (the controller keeps it hidden until the watchdog trips, so an initial `hidden` attribute is optional) |
| `[data-wc-reload]` | click reloads the page |

Mechanic attributes you may set on the loading element:

| Attribute | Effect |
|---|---|
| `data-wc-fade` | fade-out duration in ms (defaults to `fade_out_ms`) |
| `data-wc-mode` | `content` / `overlay` (affects framework CSS) |

When a custom template does not set these attributes itself, generation injects the resolved values automatically — `role="status"` (when the template does not set a `role`), `data-wc-mode`, `data-wc-interaction` (content mode), and `data-wc-fade`, plus `--wc-delay`/`--wc-fade` style variables. Template-authored values always win. If the loading element already sets its own `style` attribute, the `--wc-delay`/`--wc-fade` variables are not injected and the authored style is preserved unchanged; set `data-wc-fade` in that case so the fade duration stays configuration-driven.

The framework's base stylesheet is always emitted before the loading element, so a custom template can override any rule with its own `<style>`. Colors are theme-aware (`data-theme` on `<html>`, falling back to `prefers-color-scheme`) and overridable via CSS custom properties: `--wc-accent`, `--wc-backdrop`, `--wc-ring`, `--wc-fg`, `--wc-dormant-opacity`, `--wc-dormant-saturation`.

The loading controller is an inline classic script — sites with a strict Content-Security-Policy must allow its inline script (or use `script-src` hashing).

## Accessibility

The loading element carries `role="status"`; stage transitions are announced politely. Under `prefers-reduced-motion`, rotation, trickle, fade, and the wake-up transition are disabled while the grace period is preserved.
