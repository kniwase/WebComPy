from dataclasses import dataclass
from typing import Any

from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component, on_before_rendering
from webcompy.elements import html
from webcompy.router import Router, RouterContext, RouterLink, RouterView, use_router
from webcompy.signal import use_computed, use_state


@dataclass
class AuthSession:
    authenticated: bool = False


_SESSION = AuthSession()
_AUTH_NOTICE = ""

_ROUTE_CARD_BASE_STYLE = {
    ".route-card": {
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "padding": "var(--space-3)",
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
    },
    ".route-card h2": {
        "margin": "0 0 var(--space-2) 0",
        "font-size": "var(--font-size-lg, 1.125rem)",
    },
    ".route-card p": {
        "margin": "0 0 var(--space-3) 0",
        "color": "var(--color-fg)",
    },
}

_ACTION_LINK_STYLE = {
    ".action-link": {
        "display": "inline-block",
        "padding": "0.35rem 0.75rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-link)",
        "text-decoration": "none",
    },
    ".action-link:hover": {
        "border-color": "var(--color-link)",
    },
}

_LEAF_PANEL_STYLE = {
    ".leaf-panel": {
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "padding": "var(--space-3)",
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
    },
    ".leaf-panel h3": {
        "margin": "0 0 var(--space-2) 0",
        "font-size": "var(--font-size-base, 1rem)",
    },
    ".leaf-panel p": {
        "margin": "0",
        "color": "var(--color-fg)",
    },
}


def _auth_guard(_from_path: str, to_path: str) -> str | None:
    global _AUTH_NOTICE
    clean = to_path.split("?", 1)[0].strip("/")
    if clean == "admin" and not _SESSION.authenticated:
        _AUTH_NOTICE = "Redirected from /admin — sign in to continue."
        return "/login"
    return None


@define_component()
def HomeView(_: ComponentContext[RouterContext]):
    return html.DIV(
        {"class": "route-card"},
        html.H2({}, "Home View"),
        html.P(
            {},
            "Use the navigation bar to switch between nested workspace routes or trigger the guarded /admin route.",
        ),
        html.DIV(
            {"class": "route-actions"},
            RouterLink(to="/workspace", text=["Open Workspace"], attrs={"class": "action-link"}),
            RouterLink(to="/admin", text=["Try Protected Admin"], attrs={"class": "action-link"}),
        ),
    )


HomeView.scoped_style = {
    **_ROUTE_CARD_BASE_STYLE,
    ".route-actions": {
        "display": "flex",
        "flex-wrap": "wrap",
        "gap": "var(--space-2)",
    },
    **_ACTION_LINK_STYLE,
}


@define_component()
def WorkspaceOverview(_: ComponentContext[RouterContext]):
    return html.DIV(
        {"class": "leaf-panel"},
        html.H3({}, "Workspace Overview"),
        html.P({}, "Index child route ('') sharing WorkspaceLayout while preserving sidebar state."),
    )


WorkspaceOverview.scoped_style = _LEAF_PANEL_STYLE


@define_component()
def WorkspaceSettings(_: ComponentContext[RouterContext]):
    return html.DIV(
        {"class": "leaf-panel"},
        html.H3({}, "Workspace Settings"),
        html.P({}, "Sibling child route (/workspace/settings) mounted inside the outer layout RouterView."),
    )


WorkspaceSettings.scoped_style = _LEAF_PANEL_STYLE


@define_component()
def WorkspaceItem(context: ComponentContext[RouterContext]):
    item_id = context.props.path_params.get("item_id", "unknown")
    return html.DIV(
        {"class": "leaf-panel"},
        html.H3({}, f"Workspace Item #{item_id}"),
        html.P({}, f"Dynamic parameter item_id={item_id!r} extracted from /workspace/items/{{item_id}}."),
    )


WorkspaceItem.scoped_style = _LEAF_PANEL_STYLE


@define_component()
def WorkspaceLayout(_: ComponentContext[RouterContext]):
    sidebar_compact = use_state(lambda: False)

    def _toggle_sidebar(_ev: Any) -> None:
        sidebar_compact.value = not sidebar_compact.value

    return html.DIV(
        {"class": "workspace-shell"},
        html.ASIDE(
            {
                "class": use_computed(
                    lambda: "workspace-sidebar compact" if sidebar_compact.value else "workspace-sidebar"
                )
            },
            html.P(
                {"class": "sidebar-status"},
                use_computed(lambda: "Sidebar: compact" if sidebar_compact.value else "Sidebar: expanded"),
            ),
            html.BUTTON(
                {"type": "button", "class": "sidebar-toggle", "@click": _toggle_sidebar},
                "Toggle Sidebar",
            ),
            html.NAV(
                {"class": "sidebar-links"},
                RouterLink(to="/workspace", text=["Overview"], active_class="active", exact=True),
                RouterLink(to="/workspace/settings", text=["Settings"], active_class="active"),
                RouterLink(to="/workspace/items/42", text=["Item 42"], active_class="active"),
            ),
        ),
        html.SECTION({"class": "workspace-body"}, RouterView()),
    )


WorkspaceLayout.scoped_style = {
    ".workspace-shell": {
        "display": "grid",
        "grid-template-columns": "12rem minmax(0, 1fr)",
        "gap": "var(--space-3)",
    },
    "@media (max-width: 600px)": {
        ".workspace-shell": {
            "grid-template-columns": "minmax(0, 1fr)",
        },
    },
    ".workspace-sidebar": {
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "padding": "var(--space-3)",
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
    },
    ".workspace-sidebar.compact": {
        "background": "var(--color-bg-elevated)",
        "border-color": "var(--color-accent)",
    },
    ".sidebar-status": {
        "margin": "0 0 var(--space-2) 0",
        "font-size": "var(--font-size-sm, 0.875rem)",
        "font-weight": "600",
        "color": "var(--color-fg)",
    },
    ".sidebar-toggle": {
        "width": "100%",
        "padding": "0.35rem 0.5rem",
        "margin-bottom": "var(--space-2)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
        "cursor": "pointer",
    },
    ".sidebar-links": {
        "display": "flex",
        "flex-direction": "column",
        "gap": "0.25rem",
    },
    ".sidebar-links a": {
        "padding": "0.25rem 0.5rem",
        "border-radius": "var(--radius-sm)",
        "color": "var(--color-fg-muted)",
        "text-decoration": "none",
    },
    ".sidebar-links a.active": {
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-link)",
        "font-weight": "600",
    },
}


@define_component()
def LoginView(_: ComponentContext[RouterContext]):
    router = use_router()

    def _sign_in(_ev: Any) -> None:
        global _AUTH_NOTICE
        _SESSION.authenticated = True
        _AUTH_NOTICE = ""
        router.__set_path__("/admin", None)

    return html.DIV(
        {"class": "route-card"},
        html.H2({}, "Sign In"),
        html.P(
            {"class": "guard-notice"},
            _AUTH_NOTICE or "Sign in to unlock the /admin route.",
        ),
        html.BUTTON({"type": "button", "class": "primary-btn", "@click": _sign_in}, "Sign in as Admin"),
    )


LoginView.scoped_style = {
    **_ROUTE_CARD_BASE_STYLE,
    ".guard-notice": {
        "color": "var(--color-warning)",
        "font-weight": "600",
    },
    ".primary-btn": {
        "padding": "0.45rem 0.9rem",
        "border": "1px solid var(--color-accent)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-accent)",
        "color": "var(--color-on-accent)",
        "cursor": "pointer",
    },
}


@define_component()
def AdminView(_: ComponentContext[RouterContext]):
    router = use_router()

    def _sign_out(_ev: Any) -> None:
        _SESSION.authenticated = False
        router.__set_path__("/", None)

    return html.DIV(
        {"class": "route-card"},
        html.H2({}, "Protected Admin"),
        html.P({}, "Access granted by before_route_change guard."),
        html.BUTTON({"type": "button", "class": "secondary-btn", "@click": _sign_out}, "Sign out"),
    )


AdminView.scoped_style = {
    **_ROUTE_CARD_BASE_STYLE,
    ".secondary-btn": {
        "padding": "0.45rem 0.9rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
        "cursor": "pointer",
    },
}


@define_component()
def NotFoundView(context: ComponentContext[RouterContext]):
    return html.DIV(
        {"class": "route-card"},
        html.H2({}, "Not Found"),
        html.P({}, f"No route matched {context.props.path!r}."),
        RouterLink(to="/", text=["Return Home"], attrs={"class": "action-link"}),
    )


NotFoundView.scoped_style = {
    **_ROUTE_CARD_BASE_STYLE,
    **_ACTION_LINK_STYLE,
}


@define_component()
def RoutingDemoApp(_: ComponentContext[None]):
    @on_before_rendering
    def _reset_session() -> None:
        global _AUTH_NOTICE
        _SESSION.authenticated = False
        _AUTH_NOTICE = ""

    router = use_router()
    current_path = use_computed(lambda: (router.current_match.value.path or "/") if router.current_match.value else "/")

    return html.DIV(
        {"class": "routing-demo"},
        html.HEADER(
            {"class": "demo-header"},
            html.H1({}, "Routing & Guards Demo"),
            html.SPAN({"class": "path-badge"}, use_computed(lambda: f"Path: {current_path.value}")),
        ),
        html.NAV(
            {"class": "top-nav"},
            RouterLink(to="/", text=["Home"], active_class="active", exact=True),
            RouterLink(to="/workspace", text=["Workspace"], active_class="active"),
            RouterLink(to="/admin", text=["Admin"], active_class="active"),
            RouterLink(to="/login", text=["Login"], active_class="active"),
        ),
        html.MAIN({"class": "demo-stage"}, RouterView()),
    )


RoutingDemoApp.scoped_style = {
    ".routing-demo": {
        "font-family": "var(--font-sans, sans-serif)",
        "color": "var(--color-fg)",
        "padding": "var(--space-3)",
        "max-width": "44rem",
    },
    ".demo-header": {
        "display": "flex",
        "justify-content": "space-between",
        "align-items": "center",
        "flex-wrap": "wrap",
        "gap": "var(--space-2)",
        "margin-bottom": "var(--space-3)",
    },
    ".demo-header h1": {
        "margin": "0",
        "font-size": "var(--font-size-xl, 1.25rem)",
    },
    ".path-badge": {
        "font-family": "var(--font-mono, monospace)",
        "font-size": "var(--font-size-sm, 0.875rem)",
        "padding": "0.2rem 0.6rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
    },
    ".top-nav": {
        "display": "flex",
        "flex-wrap": "wrap",
        "gap": "var(--space-2)",
        "margin-bottom": "var(--space-3)",
        "padding-bottom": "var(--space-2)",
        "border-bottom": "1px solid var(--color-border)",
    },
    ".top-nav a": {
        "padding": "0.35rem 0.75rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-card)",
        "color": "var(--color-fg)",
        "text-decoration": "none",
    },
    ".top-nav a.active": {
        "background": "var(--color-accent)",
        "border-color": "var(--color-accent)",
        "color": "var(--color-on-accent)",
        "font-weight": "600",
    },
}

router = Router(
    {"path": "/", "component": HomeView},
    {
        "path": "/workspace",
        "component": WorkspaceLayout,
        "children": [
            {"path": "", "component": WorkspaceOverview},
            {"path": "/settings", "component": WorkspaceSettings},
            {"path": "/items/{item_id}", "component": WorkspaceItem},
        ],
    },
    {"path": "/admin", "component": AdminView},
    {"path": "/login", "component": LoginView},
    default=NotFoundView,
    mode="hash",
)
router.before_route_change.append(_auth_guard)

app = WebComPyApp(root_component=RoutingDemoApp, router=router)
app.run()
