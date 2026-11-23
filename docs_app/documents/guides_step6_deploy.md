---
title: Step 6 — Deploy
description: Wrap routed views in ErrorBoundary for runtime resilience, generate a static site bundle with webcompy generate, and understand hydration versus browser fetching.
---

# Step 6 — Deploy

In this final step (~10 minutes), you add a protective `ErrorBoundary` around your routed views and generate a deployable static site bundle with `webcompy generate`. You also review the difference between pre-rendered HTML produced at build time and live API requests run in the browser.

The live interactive demo and complete source for this step appear at the bottom of the page.

## Guarding runtime views with `ErrorBoundary`

Wrap `RouterView()` inside `ErrorBoundary` (`webcompy.elements`) with a `fallback` generator receiving `(error, reset)` so an unexpected exception inside a route view offers recovery without breaking the surrounding shell:

```python
from webcompy.elements import ErrorBoundary, html
from webcompy.router import RouterView

ErrorBoundary(
    children=lambda: RouterView(),
    fallback=lambda err, reset: html.DIV(
        {"class": "status error"},
        html.P({}, f"Something went wrong: {err}"),
        html.BUTTON({"type": "button", "@click": lambda _ev: reset()}, "Try again"),
    ),
    catch_events=True,
)
```

Async failures from `use_async_result()` are still handled inline through `load_result.is_error`, while `ErrorBoundary` catches rendering or event-callback exceptions in child components.

## Building static output with `webcompy generate`

From your project root, run:

```bash
uv run python -m webcompy generate
```

WebComPy pre-renders every configured route to HTML files inside `dist/`, bundles your Python application package wheel, copies files from `static/`, and prepares PyScript runtime assets for static hosting.

| Deployment mode | Command / output | When to use |
|---|---|---|
| Dev / ASGI server (`webcompy start`) | Live Python ASGI server (`start --dev` for hot reload) | Local development or SSR apps serving live API endpoints alongside HTML |
| Static site (`webcompy generate`) | Static `dist/` directory | Any static CDN, GitHub Pages, Netlify, or S3 bucket |

Note that static generation renders one `index.html` per declared route; apps using `mode="hash"` work out of the box on any static host even when routes are dynamic or client-only.

## What pre-rendering bakes vs what fetches at runtime

When `webcompy generate` pre-renders your app:

- **Baked into initial HTML**: static structure (heading, form markup, toolbar chrome) and initial state from `use_state` / `use_reactive_list` / `use_async_result` (which triggers hydration transfer when pre-rendering completes).
- **Executed after browser boot**: interactive event listeners, form validation on user input, client-side `HttpClient` mutations (`POST`, `PATCH`), and any browser-only work registered in `@on_mounted`.

Because Step 5's `tasks_api` middleware runs inside the browser as well as on the server, the `/api/tasks` demo behaves identically whether served dynamically or deployed from `dist/`.

## Next steps

Congratulations on completing the ToDo application tutorial! Continue exploring WebComPy by topic:

- **Basic Usage**: dive deeper into [Components](/documents/basic/components), [HTML Templates](/documents/basic/template-html), [Reactive State](/documents/basic/reactive-state), [Routing](/documents/basic/routing), [Forms](/documents/basic/forms), [HTTP & Async](/documents/basic/http-and-async), and [Error Handling](/documents/basic/error-handling).
- **Advanced Usage**: explore [SSR & SSG](/documents/advanced/ssr-and-ssg), [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer), [Custom Elements](/documents/advanced/custom-elements), [RPC Contracts](/documents/advanced/rpc-contracts), [WebSocket](/documents/advanced/websocket), and [Progressive Web App](/documents/advanced/pwa).
