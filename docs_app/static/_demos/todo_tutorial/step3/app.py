from typing import TypedDict

from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.router import Router, RouterContext, RouterLink, RouterView
from webcompy.signal import ReactiveList, Signal, SignalBase, use_computed


class TaskItem(TypedDict):
    id: int
    title: str
    done: Signal[bool]


class ToolbarProps(TypedDict):
    remaining: SignalBase[int]


def _seed_tasks() -> list[TaskItem]:
    return [
        TaskItem(id=1, title="Read Getting Started", done=Signal(True)),
        TaskItem(id=2, title="Build TodoApp state", done=Signal(False)),
        TaskItem(id=3, title="Add client-side routing", done=Signal(False)),
    ]


tasks: ReactiveList[TaskItem] = ReactiveList(_seed_tasks())


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
    ".filters a": {
        "padding": "var(--space-1) var(--space-3)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "color": "var(--color-fg)",
        "text-decoration": "none",
    },
    ".filters a.active": {
        "border-color": "var(--color-accent)",
        "color": "var(--color-accent)",
        "font-weight": "600",
    },
}


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


@define_component()
def TodoNotFoundPage(_: ComponentContext[RouterContext]):
    return html.DIV(
        {"class": "not-found"},
        html.P({}, "View not found."),
        RouterLink(to="/", text=["Back to all tasks"]),
    )


@define_component()
def TodoApp(_: ComponentContext[None]):
    tasks.value = _seed_tasks()
    remaining = use_computed(lambda: sum(1 for t in tasks.value if not t["done"].value))
    return html.DIV(
        {"class": "todo-shell"},
        html.H1({}, "ToDo Tutorial"),
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
    )


TodoApp.scoped_style = {
    ".todo-shell": {
        "max-width": "32rem",
        "font-family": "var(--font-sans)",
        "color": "var(--color-fg)",
    },
    ".task-list": {"list-style": "none", "padding": "0", "margin": "0"},
}

router = Router(
    {"path": "/", "component": TodoAllPage},
    {"path": "/active", "component": TodoActivePage},
    {"path": "/done", "component": TodoDonePage},
    default=TodoNotFoundPage,
    mode="hash",
)

app = WebComPyApp(root_component=TodoApp, router=router)
app.run()
