from contextlib import suppress

from webcompy.components import ComponentContext, define_component, on_before_destroy
from webcompy.elements import html, switch
from webcompy.router import RouterContext, RouterLink, RouterView, use_router
from webcompy.signal import use_computed, use_state

from ..components.docs_sidebar import DocsSidebar
from ..docs_manifest import prev_next


@define_component
def DocsLayout(context: ComponentContext[RouterContext]):
    router = use_router()
    mobile_open = use_state(lambda: False)

    def _current_path() -> str:
        match = router.current_match.value
        return match.path if match is not None else ""

    prev_entry = use_computed(lambda: prev_next(_current_path())[0])
    next_entry = use_computed(lambda: prev_next(_current_path())[1])

    def _toggle_mobile(_ev):
        mobile_open.value = not mobile_open.value

    def _close_mobile(_path: str):
        mobile_open.value = False

    router.after_route_change.append(_close_mobile)

    @on_before_destroy
    def _cleanup():
        with suppress(ValueError):
            router.after_route_change.remove(_close_mobile)

    return html.DIV(
        {"class": "docs-layout"},
        html.BUTTON(
            {
                "type": "button",
                "class": "docs-sidebar-toggle",
                "aria-expanded": use_computed(lambda: "true" if mobile_open.value else "false"),
                "aria-label": "Toggle documentation sidebar",
                "@click": _toggle_mobile,
            },
            "Contents",
        ),
        html.ASIDE(
            {"class": use_computed(lambda: "docs-sidebar open" if mobile_open.value else "docs-sidebar")},
            DocsSidebar(None),
        ),
        html.DIV(
            {"class": "docs-main"},
            RouterView(),
            html.FOOTER(
                {"class": "docs-pager"},
                switch(
                    {
                        "case": use_computed(lambda: prev_entry.value is not None),
                        "generator": lambda: html.DIV(
                            {"class": "docs-pager-prev"},
                            html.SPAN({"class": "docs-pager-label"}, "Previous"),
                            RouterLink(
                                to=use_computed(lambda: prev_entry.value["path"] if prev_entry.value else "/"),
                                text=[use_computed(lambda: prev_entry.value["label"] if prev_entry.value else "")],
                            ),
                        ),
                    },
                ),
                switch(
                    {
                        "case": use_computed(lambda: next_entry.value is not None),
                        "generator": lambda: html.DIV(
                            {"class": "docs-pager-next"},
                            html.SPAN({"class": "docs-pager-label"}, "Next"),
                            RouterLink(
                                to=use_computed(lambda: next_entry.value["path"] if next_entry.value else "/"),
                                text=[use_computed(lambda: next_entry.value["label"] if next_entry.value else "")],
                            ),
                        ),
                    },
                ),
            ),
        ),
    )


DocsLayout.scoped_style = {
    " .docs-layout": {
        "display": "grid",
        "grid-template-columns": "16rem minmax(0, 1fr)",
        "gap": "var(--space-6)",
        "max-width": "1400px",
        "margin": "0 auto",
        "padding": "var(--space-4) var(--space-5)",
        "align-items": "start",
    },
    " .docs-sidebar": {
        "position": "sticky",
        "top": "var(--space-4)",
    },
    " .docs-sidebar-toggle": {
        "display": "none",
        "background": "none",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "padding": "var(--space-2)",
        "font-size": "var(--font-size-base)",
        "cursor": "pointer",
        "color": "var(--color-fg)",
    },
    " .docs-main": {
        "min-width": "0",
    },
    " .docs-pager": {
        "display": "flex",
        "justify-content": "space-between",
        "gap": "var(--space-4)",
        "margin-top": "var(--space-8)",
        "padding-top": "var(--space-4)",
        "border-top": "1px solid var(--color-border)",
    },
    " .docs-pager a": {
        "color": "var(--color-fg)",
        "font-weight": "600",
        "text-decoration": "none",
    },
    " .docs-pager a:hover": {
        "color": "var(--color-link)",
    },
    " .docs-pager-label": {
        "display": "block",
        "font-size": "var(--font-size-sm)",
        "color": "var(--color-fg-muted)",
    },
    " @media (max-width: 768px)": {
        " .docs-layout": {
            "grid-template-columns": "minmax(0, 1fr)",
        },
        " .docs-sidebar-toggle": {
            "display": "block",
        },
        " .docs-sidebar": {
            "position": "static",
            "display": "none",
        },
        " .docs-sidebar.open": {
            "display": "block",
        },
    },
}
