---
title: Why WebComPy
description: Why you might choose WebComPy — and an honest account of when you should not.
---

# Why WebComPy

Choosing a framework is a trade-off. This page states both sides plainly so you can decide with open eyes.

## Why WebComPy

- **One language for the whole frontend**: components, routing, state, and data fetching are all Python. No context-switching between a Python backend and a JavaScript frontend.
- **Reactivity without ceremony**: `Signal` and `Computed` values refresh the DOM automatically. You describe what the UI should show, not how to update it.
- **Pre-rendering built in**: server-side rendering and static site generation come from the same component code — fast first loads without a separate pipeline.
- **Typed client-server flow**: schema-driven API clients and JSON-RPC (HTTP, streaming, WebSocket) keep the contract between browser and server explicit.
- **Familiar ecosystem**: the browser runtime is Python via PyScript, so libraries you already know — including numpy and friends — work where the runtime supports them.

## Why not WebComPy

At the time of writing, the following drawbacks are real. Weigh them before committing:

- **PyScript payload and cold start**: the browser must load the Python runtime before your app starts. Initial loads are heavier and slower than a hand-tuned JavaScript bundle, especially on slow networks.
- **Young ecosystem**: fewer third-party components, integrations, and answered questions than mainstream JavaScript frameworks. You will occasionally build what elsewhere you would install.
- **Performance ceiling**: Python in the browser cannot match compiled JavaScript for hot loops and large-scale DOM churn. Apps with heavy per-frame computation may need to push work to the server or to JavaScript.
- **Browser-API coverage gaps**: newer or niche web APIs may not yet have a framework wrapper, leaving you to write interop code yourself.
- **Smaller hiring and community pool**: finding developers and reviewers with WebComPy experience is harder than with established frameworks.

None of these are permanent — runtime size, coverage, and community all move over time — but they describe the framework as it exists today.

## The short version

Choose WebComPy when a Python-only stack, declarative reactivity, and built-in pre-rendering outweigh raw bundle size and ecosystem maturity for your project. If minimal cold-start latency or a vast plugin ecosystem is the top priority, a mainstream JavaScript framework is currently the safer pick.

## Next steps

Continue to the [Installation](/documents/getting-started/installation) guide to set up a project, or skim [What is WebComPy](/documents/getting-started/what-is-webcompy) for the architectural picture.
