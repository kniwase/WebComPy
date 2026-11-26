from typing import Any, TypedDict

from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.forms import min_length, required, use_field, use_form
from webcompy.router import Router, RouterContext, RouterLink, RouterView
from webcompy.signal import ReactiveList, Signal, SignalBase, use_computed, use_state
from webcompy.ui import Checkbox, FormField, Input


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
        TaskItem(id=3, title="Validate new tasks", done=Signal(False)),
    ]


tasks: ReactiveList[TaskItem] = ReactiveList(_seed_tasks())


@define_component()
def TodoItem(context: ComponentContext[TaskItem]):
    task = context.props
    return html.LI(
        {"class": use_computed(lambda: "todo-item done" if task["done"].value else "todo-item")},
        Checkbox({"value": task["done"], "aria_label": f"Toggle {task['title']}"}),
        html.SPAN({"class": "task-title"}, task["title"]),
    )


TodoItem.scoped_style = {
    ".todo-item": {
        "display": "flex",
        "align-items": "center",
        "gap": "var(--space-2)",
        "padding": "var(--space-2) var(--space-3)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
        "margin-bottom": "var(--space-2)",
    },
    ".todo-item.done .task-title": {"text-decoration": "line-through", "color": "var(--color-fg-muted)"},
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
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
        "text-decoration": "none",
    },
    ".filters a.active": {
        "background": "var(--color-accent)",
        "border-color": "var(--color-accent)",
        "color": "var(--color-on-accent)",
        "font-weight": "600",
    },
}

_TASK_LIST_STYLE = {
    ".task-list": {"list-style": "none", "padding": "0", "margin": "0"},
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


TodoAllPage.scoped_style = _TASK_LIST_STYLE


@define_component()
def TodoActivePage(_: ComponentContext[RouterContext]):
    return _render_task_list("active")


TodoActivePage.scoped_style = _TASK_LIST_STYLE


@define_component()
def TodoDonePage(_: ComponentContext[RouterContext]):
    return _render_task_list("done")


TodoDonePage.scoped_style = _TASK_LIST_STYLE


@define_component()
def TodoNotFoundPage(_: ComponentContext[RouterContext]):
    return html.DIV(
        {"class": "not-found"},
        html.P({}, "View not found."),
        RouterLink(to="/", text=["Back to all tasks"]),
    )


TodoNotFoundPage.scoped_style = {
    ".not-found": {"color": "var(--color-fg)"},
    ".not-found a": {"color": "var(--color-link)"},
}


@define_component()
def TodoApp(_: ComponentContext[None]):
    tasks.value = _seed_tasks()
    title_field = use_field(
        use_state(lambda: ""),
        validators=[required("Enter a task title"), min_length(3, "At least 3 characters")],
        name="title",
    )
    form = use_form(title=title_field)
    remaining = use_computed(lambda: sum(1 for t in tasks.value if not t["done"].value))

    def on_submit(values: dict[str, Any]) -> None:
        title = str(values["title"]).strip()
        next_id = max((t["id"] for t in tasks.value), default=0) + 1
        tasks.append(TaskItem(id=next_id, title=title, done=Signal(False)))
        form.reset()

    return html.DIV(
        {"class": "todo-shell"},
        html.H1({}, "ToDo Tutorial"),
        html.FORM(
            {"class": "todo-form", "@submit": form.submit(on_submit)},
            FormField(
                {"field": title_field, "label": "New task"},
                slots={"default": lambda: Input({"field": title_field, "placeholder": "What needs to be done?"})},
            ),
            html.BUTTON({"type": "submit"}, "Add Task"),
        ),
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
        "padding": "var(--space-3)",
        "font-family": "var(--font-sans)",
        "color": "var(--color-fg)",
    },
    ".todo-form": {
        "display": "flex",
        "align-items": "flex-end",
        "gap": "var(--space-2)",
        "margin-bottom": "var(--space-3)",
    },
    ".todo-form button": {
        "padding": "var(--space-2) var(--space-3)",
        "border": "1px solid var(--color-accent)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-accent)",
        "color": "var(--color-on-accent)",
        "cursor": "pointer",
    },
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
