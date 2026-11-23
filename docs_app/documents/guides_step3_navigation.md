---
title: Step 3 — Navigation
description: Add client-side routes for All, Active, and Done views using flat Router definitions, RouterLink active classes, and RouterView inside TodoApp.
---

# Step 3 — Navigation

In Step 3 (~10 minutes), you replace the ephemeral `filter_mode` signal with real URL routes (`/`, `/active`, `/done`) rendered through `RouterView`, and upgrade `TodoToolbar`'s slot to render `RouterLink` navigation with active styling.

The live interactive demo and complete source for this step appear at the bottom of the page.

## Sharing tasks across routed views

Each routed page component mounts when its path matches, so the task list needs to outlive an individual route transition. This tutorial keeps `tasks` in a module-level `ReactiveList` (`tasks: ReactiveList[TaskItem] = ReactiveList(_seed_tasks())`) for client-side simplicity; in server-rendered (SSR) applications, share cross-page state through Dependency Injection (covered in Advanced Usage) rather than module globals.

A small helper builds the filtered list view for all three pages:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.router import RouterContext, RouterLink
from webcompy.signal import use_computed


def _render_task_list(mode: str):
    filtered = use_computed(
        lambda: [
            t
            for t in tasks.value
            if mode == "all" or (mode == "active" and not t["done"].value) or (mode == "done" and t["done"].value)
        ]
    )
    return html.UL(
        {"class": "task-list"},
        repeat(filtered, lambda task, _key: TodoItem(task), key=lambda task: task["id"]),
    )


@define_component()
def TodoAllPage(_: ComponentContext[RouterContext]):
    return _render_task_list("all")


@define_component()
def TodoActivePage(_: ComponentContext[RouterContext]):
    return _render_task_list("active")


@define_component()
def TodoDonePage(_: ComponentContext[RouterContext]):
    return _render_task_list("done")
```

## Wiring `Router`, `RouterLink`, and `RouterView`

Pass flat route mappings and a fallback `default=TodoNotFoundPage` component to `Router(...)`, then attach the router to `WebComPyApp(root_component=TodoApp, router=router)`:

```python
from webcompy.app import WebComPyApp
from webcompy.router import Router, RouterLink, RouterView

router = Router(
    {"path": "/", "component": TodoAllPage},
    {"path": "/active", "component": TodoActivePage},
    {"path": "/done", "component": TodoDonePage},
    default=TodoNotFoundPage,
    mode="hash",
)

app = WebComPyApp(root_component=TodoApp, router=router)
```

Inside `TodoApp`, replace the filter `<button>`s in `TodoToolbar`'s `"default"` slot with `RouterLink` and render matched pages via `RouterView()`:

```python
TodoToolbar(
    {"remaining": remaining},
    slots={
        "default": lambda: html.NAV(
            {"class": "filters"},
            RouterLink(to="/", text=["All"], active_class="active", exact=True),
            RouterLink(to="/active", text=["Active"], active_class="active", exact=True),
            RouterLink(to="/done", text=["Done"], active_class="active", exact=True),
        )
    },
),
html.MAIN({}, RouterView()),
```

Remember to pass `text=[...]` as a `list` and set `exact=True` on `"/"` so `"/"` does not stay active on `"/active"` or `"/done"`. The embedded demo uses `mode="hash"` so navigation works inside an iframe URL; standalone apps deployed with `webcompy generate` or ASGI can also use `mode="history"`.

## Next steps

- Add task creation and interactive completion checkboxes in [Step 4: Forms](/documents/guides/todo-forms).
- Explore path parameters, query strings, and `use_router()` in [Routing](/documents/basic/routing).
