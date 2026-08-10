---
title: Quickstart
description: Create a WebComPy project, start the dev server, and render your first component.
---

# Quickstart

## Create a project

After installing WebComPy, scaffold a new project inside an existing Python project:

```bash
uv run python -m webcompy init
```

The command generates the application entry point, a router, and a set of example components under your project. It also creates `webcompy_config.py` so the CLI knows how to build and serve your app.

## Start the dev server

Start the development server with live reload:

```bash
uv run python -m webcompy start --dev
```

The server prints the URL of your app (default: `http://localhost:8080`). Open it in a browser to see the template page running in PyScript.

## Your first component

Components are plain functions decorated with `@define_component`. Open `app/components/home.py` and replace its body with your own view:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext


@define_component
def Home(context: ComponentContext[RouterContext]):
    context.set_title("My First App")

    return html.H1(
        {},
        "Hello WebComPy!",
    )
```

Components return an element tree built with the `html` helpers. Reactive state comes from `Signal`, `use_state`, and `use_computed`; the framework refreshes the DOM automatically when the state changes.

## Next steps

Head to the [Installation](/documents/getting-started/installation) guide for the full setup reference, or explore the demos in the navigation bar to see components, routing, and reactive state in action.