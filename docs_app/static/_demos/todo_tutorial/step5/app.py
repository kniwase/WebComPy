import json
from dataclasses import dataclass
from typing import Any, TypedDict

from webcompy.aio import AsyncWrapper
from webcompy.ajax import HttpClient
from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.elements import html, repeat, switch
from webcompy.forms import min_length, required, use_field, use_form
from webcompy.ports import (
    FetchMiddleware,
    FetchNext,
    FetchRequest,
    FetchStream,
    Response,
    add_fetch_middleware,
)
from webcompy.router import Router, RouterContext, RouterLink, RouterView
from webcompy.signal import ReactiveList, Signal, SignalBase, use_computed, use_state
from webcompy.ui import Checkbox, FormField, Input


@dataclass
class Task:
    id: int
    title: str
    done: bool


class TaskItem(TypedDict):
    id: int
    title: str
    done: Signal[bool]


class ToolbarProps(TypedDict):
    remaining: SignalBase[int]


def _json_response(payload: Any, status_code: int = 200, status_text: str = "OK") -> Response:
    return Response(
        text=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        status_code=status_code,
        status_text=status_text,
        ok=status_code < 400,
    )


def create_tasks_api() -> FetchMiddleware:
    store: list[dict[str, Any]] = [
        {"id": 1, "title": "Read Getting Started", "done": True},
        {"id": 2, "title": "Connect to /api/tasks", "done": False},
        {"id": 3, "title": "Prepare for static deploy", "done": False},
    ]

    async def tasks_api(request: FetchRequest, next: FetchNext) -> Response | FetchStream:
        path = request.url.split("?", 1)[0]
        raw_body = request.body.decode("utf-8") if isinstance(request.body, bytes) else (request.body or "{}")
        if path == "/api/tasks" and request.method == "GET":
            return _json_response(store)
        if path == "/api/tasks" and request.method == "POST":
            payload = json.loads(raw_body)
            title = str(payload.get("title", "")).strip()
            if not title:
                return _json_response({"error": "title required"}, 400, "Bad Request")
            created = {"id": max((t["id"] for t in store), default=0) + 1, "title": title, "done": False}
            store.append(created)
            return _json_response(created, 201, "Created")
        if path.startswith("/api/tasks/") and request.method == "PATCH":
            task_id = int(path.rsplit("/", 1)[-1])
            payload = json.loads(raw_body)
            for item in store:
                if item["id"] == task_id:
                    item["done"] = bool(payload.get("done", False))
                    return _json_response(item)
            return _json_response({"error": "not found"}, 404, "Not Found")
        return await next(request)

    return tasks_api


tasks: ReactiveList[TaskItem] = ReactiveList([])


def _to_item(task: Task) -> TaskItem:
    return TaskItem(id=task.id, title=task.title, done=Signal(task.done))


@define_component()
def TodoItem(context: ComponentContext[TaskItem]):
    task = context.props

    @AsyncWrapper()
    async def persist_done(checked: bool) -> None:
        await HttpClient.patch(f"/api/tasks/{task['id']}", json={"done": checked}, response_type=Task)

    return html.LI(
        {"class": use_computed(lambda: "todo-item done" if task["done"].value else "todo-item")},
        Checkbox({"value": task["done"], "on_change": persist_done, "aria_label": f"Toggle {task['title']}"}),
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
    add_fetch_middleware(create_tasks_api())
    tasks.value = []

    async def load_tasks() -> list[Task]:
        loaded = await HttpClient.get("/api/tasks", response_type=list[Task])
        tasks.value = [_to_item(t) for t in loaded]
        return loaded

    load_result = use_async_result(load_tasks)
    title_field = use_field(
        use_state(lambda: ""),
        validators=[required("Enter a task title"), min_length(3, "At least 3 characters")],
        name="title",
    )
    form = use_form(title=title_field)
    remaining = use_computed(lambda: sum(1 for t in tasks.value if not t["done"].value))

    async def on_submit(values: dict[str, Any]) -> None:
        created = await HttpClient.post("/api/tasks", json={"title": str(values["title"]).strip()}, response_type=Task)
        tasks.append(_to_item(created))
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
            html.BUTTON({"type": "submit", "disabled": form.submitting}, "Add Task"),
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
        switch(
            {
                "case": load_result.is_error,
                "generator": lambda: html.DIV(
                    {"class": "status error"},
                    html.P({}, f"Failed to load tasks: {load_result.error.value}"),
                    html.BUTTON({"type": "button", "@click": lambda _ev: load_result.refetch()}, "Retry"),
                ),
            },
            {"case": load_result.is_success, "generator": lambda: html.MAIN({}, RouterView())},
            default=lambda: html.P({"class": "status"}, "Loading tasks..."),
        ),
    )


TodoApp.scoped_style = {
    ".todo-shell": {
        "max-width": "32rem",
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
        "color": "#ffffff",
        "cursor": "pointer",
    },
    ".task-list": {"list-style": "none", "padding": "0", "margin": "0"},
    ".status": {"color": "var(--color-fg-muted)", "font-size": "var(--font-size-sm)"},
    ".status.error": {"color": "var(--color-danger)"},
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
