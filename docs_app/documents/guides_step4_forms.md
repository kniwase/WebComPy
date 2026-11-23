---
title: Step 4 — Forms
description: Add a validated task-creation form with use_field(), use_form(), FormField, and Input, and toggle task completion with Checkbox.
---

# Step 4 — Forms

In Step 4 (~15 minutes), your ToDo app becomes interactive: users can add new tasks through a validated form using `use_field` and `use_form`, see accessible validation messages on blur or invalid submit, and toggle task completion live across routes using `Checkbox`.

The live interactive demo and complete source for this step appear at the bottom of the page.

## Validating input with `use_field()` and `use_form()`

Inside `TodoApp`, wrap a string `Signal` in `use_field(...)` with built-in `required` and `min_length` validators, then group it into a `Form` with `use_form(...)`:

```python
from typing import Any

from webcompy.forms import min_length, required, use_field, use_form
from webcompy.signal import Signal, use_state

title_field = use_field(
    use_state(lambda: ""),
    validators=[required("Enter a task title"), min_length(3, "At least 3 characters")],
    name="title",
)
form = use_form(title=title_field)


def on_submit(values: dict[str, Any]) -> None:
    title = str(values["title"]).strip()
    next_id = max((t["id"] for t in tasks.value), default=0) + 1
    tasks.append(TaskItem(id=next_id, title=title, done=Signal(False)))
    form.reset()
```

`form.submit(on_submit)` calls `preventDefault()`, marks all fields touched, aborts when `form.valid.value` is `False`, and otherwise executes `on_submit(values)`. Calling `form.reset()` clears the input back to `""` and resets `touched` and `dirty` so errors do not linger after adding a task.

## Rendering controls with `FormField`, `Input`, and `:bind`

Wrap `Input` inside `FormField` so the `<label>`, `<input>`, and validation error region link automatically via accessible IDs and show errors only once the field is touched and invalid:

```python
from webcompy.elements import html
from webcompy.ui import FormField, Input

html.FORM(
    {"class": "todo-form", "@submit": form.submit(on_submit)},
    FormField(
        {"field": title_field, "label": "New task"},
        slots={"default": lambda: Input({"field": title_field, "placeholder": "What needs to be done?"})},
    ),
    html.BUTTON({"type": "submit"}, "Add Task"),
)
```

Under the hood, `Input` uses WebComPy's native two-way `:bind` attribute (`html.INPUT({":bind": title_field, ...})`), which synchronizes the DOM value with `title_field.value` and updates `dirty` on input and `touched` on blur.

## Toggling completion with `Checkbox`

Update `TodoItem` to render a `Checkbox` bound in live `value=` mode directly to each task's `Signal[bool]`:

```python
from webcompy.ui import Checkbox

Checkbox({"value": task["done"], "aria_label": f"Toggle {task['title']}"})
```

Because `visible_tasks` and `remaining` read `t["done"].value` inside `use_computed`, checking or unchecking an item immediately crosses out the title, updates the remaining counter, and moves the item between `/active` and `/done`.

## Next steps

- Replace local in-memory seeding with HTTP loading and persistence in [Step 5: Remote Data](/documents/guides/todo-remote-data).
- Explore all built-in validators and UI form controls in [Forms](/documents/basic/forms) and [UI Primitives](/documents/basic/ui-primitives).
