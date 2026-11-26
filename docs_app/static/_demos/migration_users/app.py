import json
from dataclasses import dataclass
from typing import Any, TypedDict

from webcompy.ajax import HttpClient
from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.elements import html, switch
from webcompy.ports import (
    FetchMiddleware,
    FetchNext,
    FetchRequest,
    FetchStream,
    Response,
    add_fetch_middleware,
)
from webcompy.signal import Computed, ReactiveList, use_reactive_list, use_state
from webcompy.template import render_template


@dataclass
class User:
    id: int
    name: str
    email: str
    role: str
    active: bool


_SEEDED_USERS: list[dict[str, Any]] = [
    {"id": 1, "name": "Alice Chen", "email": "alice@example.com", "role": "admin", "active": True},
    {"id": 2, "name": "Bob Martinez", "email": "bob@example.com", "role": "editor", "active": True},
    {"id": 3, "name": "Carol Okafor", "email": "carol@example.com", "role": "viewer", "active": True},
    {"id": 4, "name": "David Kim", "email": "david@example.com", "role": "editor", "active": False},
    {"id": 5, "name": "Elena Novak", "email": "elena@example.com", "role": "admin", "active": True},
    {"id": 6, "name": "Frank Sato", "email": "frank@example.com", "role": "viewer", "active": True},
]


def _json_response(payload: Any, status_code: int = 200, status_text: str = "OK") -> Response:
    return Response(
        text=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        status_code=status_code,
        status_text=status_text,
        ok=status_code < 400,
    )


def create_users_mock() -> FetchMiddleware:
    async def users_mock(request: FetchRequest, next: FetchNext) -> Response | FetchStream:
        path = request.url.split("?", 1)[0]
        if path == "/api/users" and request.method == "GET":
            return _json_response(list(_SEEDED_USERS))
        return await next(request)

    return users_mock


class PageShellProps(TypedDict):
    title: str


@define_component()
def PageShell(context: ComponentContext[PageShellProps]):
    return html.DIV(
        {"class": "page-shell"},
        html.HEADER(
            {"class": "shell-header"},
            html.H1({}, context.props["title"]),
            html.SPAN({"class": "shell-badge"}, "Live SPA"),
        ),
        html.MAIN({"class": "shell-main"}, context.slots("default")),
    )


PageShell.scoped_style = {
    ".page-shell": {
        "font-family": "var(--font-sans, sans-serif)",
        "padding": "var(--space-3)",
        "color": "var(--color-fg)",
        "max-width": "42rem",
    },
    ".shell-header": {
        "display": "flex",
        "align-items": "center",
        "justify-content": "space-between",
        "padding-bottom": "var(--space-2)",
        "border-bottom": "1px solid var(--color-border)",
        "margin-bottom": "var(--space-3)",
    },
    ".shell-header h1": {
        "margin": "0",
        "font-size": "var(--font-size-xl, 1.25rem)",
    },
    ".shell-badge": {
        "font-size": "0.75rem",
        "padding": "0.15rem 0.5rem",
        "border-radius": "var(--radius-sm)",
        "border": "1px solid var(--color-border)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-link)",
        "font-weight": "600",
    },
}


@define_component()
def UserDirectory(_: ComponentContext[None]):
    query = use_state(lambda: "")
    role_filter = use_state(lambda: "all")
    users: ReactiveList[User] = use_reactive_list(lambda: [])

    async def _load_users() -> list[User]:
        loaded = await HttpClient.get("/api/users", response_type=list[User])
        users.value = loaded
        return loaded

    users_result = use_async_result(_load_users)

    filtered_users = Computed(
        lambda: [
            user
            for user in users.value
            if (role_filter.value == "all" or user.role == role_filter.value)
            and (
                not query.value.strip()
                or query.value.strip().lower() in user.name.lower()
                or query.value.strip().lower() in user.email.lower()
            )
        ]
    )

    summary_text = Computed(lambda: f"Showing {len(filtered_users.value)} of {len(users.value)} users")

    def _set_role(role: str):
        def _handler(_ev: Any) -> None:
            role_filter.value = role

        return _handler

    def _clear_filters(_ev: Any) -> None:
        query.value = ""
        role_filter.value = "all"

    def _render_results():
        return render_template(
            """
            <div class="users-results">
                <ul class="user-list">
                    {% for user in filtered_users %}
                        <li class="user-item">
                            <div class="user-primary">
                                <strong>{{ user.name }}</strong>
                                <span class="user-email">{{ user.email }}</span>
                            </div>
                            <div class="user-badges">
                                <span class="role-badge">{{ user.role | title }}</span>
                                <span class="status-badge">{{ "Active" if user.active else "Inactive" }}</span>
                            </div>
                        </li>
                    {% endfor %}
                </ul>
                {% if not filtered_users %}
                    <p class="empty-state">No matching users.</p>
                {% endif %}
            </div>
            """,
            {"filtered_users": filtered_users},
        )

    role_buttons = [
        html.BUTTON(
            {
                "type": "button",
                "class": Computed(lambda r=role: "role-btn active" if role_filter.value == r else "role-btn"),
                "@click": _set_role(role),
            },
            label,
        )
        for role, label in [("all", "All"), ("admin", "Admin"), ("editor", "Editor"), ("viewer", "Viewer")]
    ]

    return html.DIV(
        {"class": "users-demo"},
        html.DIV(
            {"class": "controls"},
            html.INPUT(
                {
                    "type": "search",
                    "class": "search-input",
                    "placeholder": "Filter by name or email...",
                    "aria-label": "Filter users",
                    ":bind": query,
                }
            ),
            html.BUTTON({"type": "button", "class": "clear-btn", "@click": _clear_filters}, "Clear"),
        ),
        html.DIV({"class": "role-tabs", "role": "group", "aria-label": "Filter by role"}, *role_buttons),
        html.P({"class": "user-summary"}, summary_text),
        switch(
            {"case": users_result.is_success, "generator": _render_results},
            default=lambda: html.P({"class": "loading-state"}, "Loading users..."),
        ),
    )


UserDirectory.scoped_style = {
    ".controls": {
        "display": "flex",
        "gap": "var(--space-2)",
        "margin-bottom": "var(--space-2)",
    },
    ".search-input": {
        "flex": "1",
        "min-width": "0",
        "padding": "0.4rem 0.6rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg)",
        "color": "var(--color-fg)",
    },
    ".clear-btn, .role-btn": {
        "padding": "0.35rem 0.7rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
        "cursor": "pointer",
    },
    ".role-tabs": {
        "display": "flex",
        "flex-wrap": "wrap",
        "gap": "var(--space-2)",
        "margin-bottom": "var(--space-2)",
    },
    ".role-btn.active": {
        "background": "var(--color-accent)",
        "border-color": "var(--color-accent)",
        "color": "var(--color-on-accent)",
        "font-weight": "600",
    },
    ".user-summary": {
        "font-size": "var(--font-size-sm, 0.875rem)",
        "color": "var(--color-fg-muted)",
        "margin": "0 0 var(--space-2) 0",
    },
    ".user-list": {
        "list-style": "none",
        "padding": "0",
        "margin": "0",
    },
    ".user-list:empty": {
        "display": "none",
    },
    ".user-item": {
        "display": "flex",
        "justify-content": "space-between",
        "align-items": "center",
        "flex-wrap": "wrap",
        "gap": "var(--space-2)",
        "padding": "var(--space-2) var(--space-3)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "margin-bottom": "var(--space-2)",
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
    },
    ".user-primary": {
        "display": "flex",
        "flex-direction": "column",
        "gap": "0.15rem",
    },
    ".user-email": {
        "font-size": "var(--font-size-sm, 0.875rem)",
        "color": "var(--color-fg-muted)",
    },
    ".user-badges": {
        "display": "flex",
        "gap": "var(--space-2)",
        "font-size": "0.75rem",
    },
    ".role-badge, .status-badge": {
        "padding": "0.15rem 0.5rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
    },
    ".empty-state, .loading-state": {
        "padding": "var(--space-3)",
        "border": "1px dashed var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "color": "var(--color-fg-muted)",
    },
}


@define_component()
def MigrationUsersApp(_: ComponentContext[None]):
    add_fetch_middleware(create_users_mock())
    return PageShell(
        {"title": "Team Directory"},
        slots={"default": lambda: UserDirectory(None)},
    )


app = WebComPyApp(root_component=MigrationUsersApp)
app.run()
