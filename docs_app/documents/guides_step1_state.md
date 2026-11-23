---
title: Step 1 — App Shell and Reactive State
description: Model tasks in a ReactiveList, track a filter signal with use_state, derive counts and filtered views with use_computed, and render keyed lists with repeat().
---

# Step 1 — App Shell and Reactive State

In this first step (~10 minutes), you build the root `TodoApp` shell with three seeded tasks, reactive filter buttons (`All`, `Active`, `Done`), and a live counter showing how many tasks remain. There are no input forms or subcomponents yet — the goal is to wire reactive state and keyed list rendering cleanly.

The live interactive demo and complete source for this step appear at the bottom of the page.

## Defining task state with `use_reactive_list()` and `Signal`

Each task stores an integer `id`, a `title`, and a reactive `done` cell (`Signal[bool]`) so individual completion flags can update later without replacing the whole list:

```python
from typing import TypedDict

from webcompy.signal import Signal, use_reactive_list, use_state


class TaskItem(TypedDict):
    id: int
    title: str
    done: Signal[bool]
```

Inside `TodoApp`, initialize both `tasks` and `filter_mode` with factory callables (`lambda: ...`) so setup stays friendly to pre-rendering and hydration:

```python
tasks = use_reactive_list(
    lambda: [
        TaskItem(id=1, title="Read Getting Started", done=Signal(True)),
        TaskItem(id=2, title="Build TodoApp state", done=Signal(False)),
        TaskItem(id=3, title="Split into components", done=Signal(False)),
    ]
)
filter_mode = use_state(lambda: "all")
```

## Deriving counts and filtered views with `use_computed()`

Derived values compute automatically whenever `tasks.value`, any task's `done.value`, or `filter_mode.value` changes:

```python
from webcompy.signal import use_computed

remaining = use_computed(lambda: sum(1 for t in tasks.value if not t["done"].value))
visible_tasks = use_computed(
    lambda: [
        t
        for t in tasks.value
        if filter_mode.value == "all"
        or (filter_mode.value == "active" and not t["done"].value)
        or (filter_mode.value == "done" and t["done"].value)
    ]
)
```

Because `use_computed` tracks every signal read during execution, you never have to subscribe or recalculate counts manually when switching filters or toggling tasks.

## Rendering keyed lists with `repeat()` and filter buttons

Pass `visible_tasks` to `repeat(..., key=lambda task: task["id"])` inside `html.UL(...)`. Supplying a stable `key=` lets WebComPy reuse existing `<li>` nodes across filter switches:

```python
from webcompy.elements import html, repeat

html.UL(
    {"class": "task-list"},
    repeat(
        visible_tasks,
        lambda task, _key: html.LI(
            {"class": use_computed(lambda: "todo-item done" if task["done"].value else "todo-item")},
            task["title"],
        ),
        key=lambda task: task["id"],
    ),
)
```

Each filter button updates `filter_mode.value` on `@click` and highlights the selected button using a computed `"class"` attribute. Attach CSS rules to `TodoApp.scoped_style` using WebComPy's semantic design tokens (`var(--color-accent)`, `var(--space-2)`).

## Next steps

- Extract `TodoItem` and `TodoToolbar` into reusable components in [Step 2: Components](/documents/guides/todo-components).
- Review reactive primitives in [Reactive State](/documents/basic/reactive-state) and list reconciliation in [Elements & Events](/documents/basic/elements-and-events).
