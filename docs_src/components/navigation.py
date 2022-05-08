from typing import List, TypedDict
from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterLink


class _SubPage(TypedDict):
    title: str
    to: str


class _PageRequired(TypedDict):
    title: str


class Page(_PageRequired, total=False):
    to: str
    children: List[_SubPage]


@define_component
def Navbar(context: ComponentContext[List[Page]]):
    def generate_navitem(page: Page, idx: int):
        if "children" in page:
            main = (
                [
                    html.LI(
                        {},
                        RouterLink(
                            to=page["to"],
                            text=[page["title"]],
                            attrs={"class": "dropdown-item"},
                        ),
                    ),
                    html.LI(
                        {"class": "dropdown-item"},
                        html.HR({"class": "dropdown-divider"}),
                    ),
                ]
                if "to" in page
                else []
            )
            items = tuple(
                html.LI(
                    {},
                    RouterLink(
                        to=sub["to"],
                        text=[sub["title"]],
                        attrs={"class": "dropdown-item"},
                    ),
                )
                for sub in page["children"]
            )
            return html.LI(
                {"class": "nav-item dropdown"},
                html.A(
                    {
                        "id": f"navbar-dropdown-{idx}",
                        "class": "nav-link dropdown-toggle",
                        "data-bs-toggle": "dropdown",
                        "role": "button",
                        "data-bs-toggle": "dropdown",
                        "aria-expanded": "false",
                    },
                    page["title"],
                ),
                html.UL(
                    {
                        "class": "dropdown-menu",
                        "aria-labelledby": f"navbar-dropdown-{idx}",
                    },
                    *main,
                    *items,
                ),
            )
        if "to" in page:
            return html.LI(
                {"class": "nav-item"},
                RouterLink(
                    to=page["to"],
                    text=[page["title"]],
                    attrs={"class": "nav-link"},
                ),
            )
        return None

    return html.NAV(
        {"class": "navbar navbar-expand-md navbar-light bg-light"},
        html.DIV(
            {"class": "container-fluid"},
            html.SPAN(
                {"class": "navbar-brand mb-0 h1"},
                "WebComPy",
            ),
            html.BUTTON(
                {
                    "class": "navbar-toggler",
                    "type": "button",
                    "data-bs-toggle": "collapse",
                    "data-bs-target": "#navbarNav",
                    "aria-controls": "navbarNav",
                    "aria-expanded": "false",
                    "aria-label": "Toggle navigation",
                },
                html.SPAN({"class": "navbar-toggler-icon"}),
            ),
            html.DIV(
                {"class": "collapse navbar-collapse", "id": "navbarNav"},
                html.UL(
                    {"class": "navbar-nav"},
                    *tuple(
                        generate_navitem(page, idx)
                        for idx, page in enumerate(context.props)
                    ),
                ),
            ),
        ),
    )
