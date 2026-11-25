---
title: What is WebComPy
description: Framework positioning, the dual-environment model, core promises, and the relationship to FastAPI and Starlette.
---

# What is WebComPy

WebComPy is a Python frontend framework. You write your UI in Python — components, routing, and state — and the same codebase runs in two places: in the browser via PyScript, and on the server via standard Python for pre-rendering.

## The dual-environment model

Every WebComPy app lives in two runtimes:

- **Browser (PyScript/Emscripten)**: reactive components render into the DOM, handle events, and update the page. This is where your app is interactive.
- **Server (standard Python)**: the same components render to HTML for server-side rendering (SSR) and static site generation (SSG), so first loads are fast and crawlable.

```text
Python components
     |-- browser --> interactive DOM (PyScript)
     |-- server  --> pre-rendered HTML (SSR / SSG)
```

The framework detects the runtime with `platform.system() == "Emscripten"` and wires up the matching port implementations (DOM, fetch, scheduler) through dependency injection. Application code stays the same on both sides.

## Core promises

- **Components**: plain functions decorated with `@define_component()` render as Light DOM custom elements. Props, slots, and scoped CSS included.
- **Reactivity**: `Signal`, `Computed`, and reactive collections refresh the DOM automatically when state changes.
- **Routing**: client-side routing with history and hash modes, path parameters, and navigation hooks.
- **CLI and pre-rendering**: scaffold projects, run a dev server with live reload, and ship SSR or fully static output.
- **Typed data flow**: schema-driven API clients, JSON-RPC with streaming and WebSocket transports, and server-to-browser hydration transfer.

## Relationship to FastAPI and Starlette

WebComPy is not a replacement for your backend framework — it complements it:

- The **dev server and SSR endpoints are ASGI apps**. You can embed a WebComPy serving app inside a host ASGI application (for example, next to FastAPI routes) and share the same process.
- **Data fetching during SSR** goes through the same ASGI transport, so server-rendered pages can call your own API routes without leaving the process.
- For typed client-server communication, WebComPy offers its own **JSON-RPC layer** (HTTP, streaming, and WebSocket), which sits alongside — not instead of — plain REST endpoints you already serve.
- Already running a server-rendered Jinja2 + FastAPI app? Follow the step-by-step strangler strategy in [Migrating from Jinja2 + FastAPI](/documents/migration/from-jinja2-fastapi).

## Next steps

If WebComPy sounds like a fit, read [Why WebComPy](/documents/getting-started/why-webcompy) for an honest discussion of trade-offs, then follow the [Installation](/documents/getting-started/installation) guide to set up a project.
