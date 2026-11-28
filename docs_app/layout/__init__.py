from webcompy.components import ComponentContext, define_component
from webcompy.di import inject
from webcompy.di._keys import _ROUTER_KEY
from webcompy.elements import html
from webcompy.router import RouterView
from webcompy.signal import use_computed

from ..components.navigation import DocsNavbar, Page
from ..docs_manifest import DOCS_SECTIONS


@define_component()
def DocsRoot(_: ComponentContext[None]):
    router = inject(_ROUTER_KEY, default=None)

    def _skip_href() -> str:
        if router is None:
            return "#main-content"
        match = router.current_match.value
        if match is None:
            return "#main-content"
        path = match.path if match.path.startswith("/") else "/" + match.path
        return f"{path}#main-content"

    skip_href = use_computed(_skip_href)

    pages: list[Page] = [
        {
            "title": "Home",
            "to": "/",
        },
        {
            "title": "Documents",
            "to": "/documents",
            "groups": [
                {
                    "title": section["title"],
                    "items": [
                        {
                            "title": page["label"],
                            "to": page["path"],
                        }
                        for page in section["pages"]
                    ],
                }
                for section in DOCS_SECTIONS
            ],
        },
    ]
    return html.DIV(
        {},
        html.A({"class": "skip-link", "href": skip_href}, "Skip to main content"),
        DocsNavbar(pages),
        html.MAIN(
            {"id": "main-content", "tabindex": "-1"},
            html.ARTICLE(
                {},
                RouterView(),
            ),
        ),
    )


DocsRoot.scoped_style = {
    ".skip-link": {
        "position": "fixed",
        "top": "var(--space-3)",
        "left": "var(--space-3)",
        "z-index": "2000",
        "padding": "var(--space-2) var(--space-4)",
        "background-color": "var(--color-accent)",
        "color": "var(--color-on-accent)",
        "border-radius": "var(--radius-sm)",
        "font-weight": "600",
        "text-decoration": "none",
        "transform": "translateY(-200%)",
        "transition": "transform 0.15s ease",
    },
    ".skip-link:focus": {
        "transform": "translateY(0)",
        "outline": "2px solid var(--color-fg)",
        "outline-offset": "2px",
    },
    ".skip-link:focus-visible": {
        "transform": "translateY(0)",
        "outline": "2px solid var(--color-fg)",
        "outline-offset": "2px",
    },
}
