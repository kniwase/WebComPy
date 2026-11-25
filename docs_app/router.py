from webcompy.router import Router, lazy

from .docs_manifest import route_children
from .pages.not_found import NotFound

router = Router(
    {"path": "/", "component": lazy("docs_app.pages.home:HomePage", __file__)},
    {
        "path": "/documents",
        "component": lazy("docs_app.layout.document:DocsLayout", __file__),
        "children": route_children(),
    },
    default=NotFound,
    mode="history",
    base_url="",
)
