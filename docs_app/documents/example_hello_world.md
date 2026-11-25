---
title: Hello World
description: Minimal WebComPy application demonstrating @define_component, ComponentContext, html helpers, and WebComPyApp bootstrapping.
---

# Hello World

This example shows the smallest complete WebComPy application running in an isolated PyScript runtime: a single Light DOM component mounted at `#webcompy-app` with zero JavaScript boilerplate.

Use this structure when checking your environment, testing a standalone widget, or starting a minimal single-view app without routing.

## What this demonstrates

- **Function component definition**: `@define_component("hello-world-app")` registers a Light DOM custom element wrapping the returned virtual elements cleanly (or omit the argument to derive the tag from the function name).
- **Declarative elements**: `html.DIV({}, html.H1({}, "Hello WebComPy!"))` constructs typed elements directly in Python without string templates.
- **Browser bootstrap**: Creating `app = WebComPyApp(root_component=HelloWorld)` and calling `app.run()` mounts the component inside the page's `#webcompy-app` container.

## Key mechanisms and how to adapt

1. **Swap to derived tag names**: Rename `@define_component("hello-world-app")` to `@define_component()` when the snake-to-kebab name (`<hello-world>`) already has a hyphen and matches your desired custom element tag.
2. **Add local reactive state**: Introduce `count = use_state(lambda: 0)` inside the function body and bind an `@click` handler to make the view interactive.
3. **Add scoped CSS**: Assign `HelloWorld.scoped_style = {"h1": {"color": "var(--color-accent)"}}` below the component definition to style nodes inside the component without leaking rules outside.

## Next steps

- Continue to [ToDo List](/documents/examples/todo) for reactive lists, conditional rendering, and child components.
- Learn component props, slots, and lifecycle hooks in [Components](/documents/basic/components) and [What is WebComPy](/documents/getting-started/what-is-webcompy).
- Follow the multi-step build guide in [Guides Overview](/documents/guides/overview).
