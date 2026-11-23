---
title: Step 2 — Components
description: Extract TodoItem and TodoToolbar into reusable @define_component() components using props, named slots, and component-scoped styles.
---

# Step 2 — Components

In Step 2 (~10 minutes), you split the monolithic `TodoApp` from Step 1 into focused UI building blocks: `TodoItem` for a single task row and `TodoToolbar` for the remaining count plus customizable filter controls.

The live interactive demo and complete source for this step appear at the bottom of the page.

## Defining multi-word components with `@define_component()`

Call `@define_component()` with parentheses so WebComPy derives the Light DOM custom element tag from the PascalCase function name (`TodoItem` becomes `<todo-item>`, `TodoToolbar` becomes `<todo-toolbar>`, and `TodoApp` becomes `<todo-app>`):

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import use_computed


@define_component()
def TodoItem(context: ComponentContext[TaskItem]):
    task = context.props
    return html.LI(
        {"class": use_computed(lambda: "todo-item done" if task["done"].value else "todo-item")},
        html.SPAN({}, task["title"]),
    )
```

Moving `.todo-item` rules onto `TodoItem.scoped_style` keeps item styling encapsulated alongside its markup.

## Passing props and default slots into `TodoToolbar`

`TodoToolbar` receives a `remaining` signal in `context.props` and renders custom filter controls passed through its `"default"` slot via `context.slots("default", fallback=lambda: None)`:

```python
from typing import TypedDict

from webcompy.signal import SignalBase


class ToolbarProps(TypedDict):
    remaining: SignalBase[int]


@define_component()
def TodoToolbar(context: ComponentContext[ToolbarProps]):
    remaining = context.props["remaining"]
    return html.DIV(
        {"class": "toolbar"},
        html.SPAN({"class": "remaining"}, use_computed(lambda: f"{remaining.value} remaining")),
        context.slots("default", fallback=lambda: None),
    )
```

In `TodoApp`, pass the filter button strip inside `slots={"default": lambda: ...}`:

```python
TodoToolbar(
    {"remaining": remaining},
    slots={
        "default": lambda: html.DIV(
            {"class": "filters"},
            filter_button("All", "all"),
            filter_button("Active", "active"),
            filter_button("Done", "done"),
        )
    },
)
```

Keeping the navigation region as a slot prepares `TodoToolbar` for Step 3, where those buttons become router links without rewriting `TodoToolbar` itself.

## Next steps

- Replace local filter buttons with client-side routes in [Step 3: Navigation](/documents/guides/todo-navigation).
- Learn more about component tag derivation, props, slots, and `:host` styling in [Components](/documents/basic/components).
