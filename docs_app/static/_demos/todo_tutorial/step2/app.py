from typing import TypedDict

from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.signal import Signal, SignalBase, use_computed, use_reactive_list, use_state


class TaskItem(TypedDict):
    id: int
    title: str
    done: Signal[bool]


class ToolbarProps(TypedDict):
    remaining: SignalBase[int]


@define_component()
def TodoItem(context: ComponentContext[TaskItem]):
    task = context.props
    return html.LI(
        {"class": use_computed(lambda: "todo-item done" if task["done"].value else "todo-item")},
        html.SPAN({}, task["title"]),
    )


TodoItem.scoped_style = {
    ".todo-item": {
        "padding": "var(--space-2) var(--space-3)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
        "margin-bottom": "var(--space-2)",
    },
    ".todo-item.done": {"text-decoration": "line-through", "color": "var(--color-fg-muted)"},
}


@define_component()
def TodoToolbar(context: ComponentContext[ToolbarProps]):
    remaining = context.props["remaining"]
    return html.DIV(
        {"class": "toolbar"},
        html.SPAN({"class": "remaining"}, use_computed(lambda: f"{remaining.value} remaining")),
        context.slots("default", fallback=lambda: None),
    )


TodoToolbar.scoped_style = {
    ".toolbar": {
        "display": "flex",
        "justify-content": "space-between",
        "align-items": "center",
        "gap": "var(--space-2)",
        "margin": "var(--space-3) 0",
    },
    ".filters": {"display": "flex", "gap": "var(--space-2)"},
    ".filters button": {
        "padding": "var(--space-1) var(--space-3)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
        "cursor": "pointer",
    },
    ".filters button.active": {
        "background": "var(--color-accent)",
        "border-color": "var(--color-accent)",
        "color": "var(--color-on-accent)",
        "font-weight": "600",
    },
}


@define_component()
def TodoApp(_: ComponentContext[None]):
    tasks = use_reactive_list(
        lambda: [
            TaskItem(id=1, title="Read Getting Started", done=Signal(True)),
            TaskItem(id=2, title="Build TodoApp state", done=Signal(False)),
            TaskItem(id=3, title="Split into components", done=Signal(False)),
        ]
    )
    filter_mode = use_state(lambda: "all")

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

    def filter_button(label: str, mode: str):
        return html.BUTTON(
            {
                "type": "button",
                "class": use_computed(lambda: "active" if filter_mode.value == mode else ""),
                "@click": lambda _ev: setattr(filter_mode, "value", mode),
            },
            label,
        )

    return html.DIV(
        {"class": "todo-shell"},
        html.H1({}, "ToDo Tutorial"),
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
        ),
        html.UL(
            {"class": "task-list"},
            repeat(visible_tasks, lambda task, _key: TodoItem(task), key=lambda task: task["id"]),
        ),
    )


TodoApp.scoped_style = {
    ".todo-shell": {
        "max-width": "32rem",
        "padding": "var(--space-3)",
        "font-family": "var(--font-sans)",
        "color": "var(--color-fg)",
    },
    ".task-list": {"list-style": "none", "padding": "0", "margin": "0"},
}

app = WebComPyApp(root_component=TodoApp)
app.run()
