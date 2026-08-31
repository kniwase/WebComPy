from webcompy.components import ComponentContext, define_component, on_mounted
from webcompy.di import inject
from webcompy.elements import html
from webcompy.ports import ASYNC_SCHEDULER_PORT_KEY, RESOURCE_PORT_KEY
from webcompy.router import RouterView

from ..components.navigation import DocsNavbar, Page
from ..docs_manifest import flatten_pages, route_pages


@define_component()
def DocsRoot(_: ComponentContext[None]):
    @on_mounted
    def _prefetch_docs_resources():
        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY, default=None)
        port = inject(RESOURCE_PORT_KEY, default=None)
        if scheduler is None or port is None:
            return
        sources = [page["source"] for page in route_pages() if "source" in page]
        scheduler.schedule(port.preload(sources), render=False)

    pages: list[Page] = [
        {
            "title": "Home",
            "to": "/",
        },
        {
            "title": "Documents",
            "to": "/documents",
            "children": [
                {
                    "title": page["label"],
                    "to": page["path"],
                }
                for page in flatten_pages()
            ],
        },
        {
            "title": "Demos",
            # "to": "/sample",
            "children": [
                {
                    "title": "HelloWorld",
                    "to": "/sample/helloworld",
                },
                {
                    "title": "FizzBuzz",
                    "to": "/sample/fizzbuzz",
                },
                {
                    "title": "ToDo List",
                    "to": "/sample/todo",
                },
                {
                    "title": "Matplotlib Sample",
                    "to": "/sample/matplotlib",
                },
                {
                    "title": "Fetch Sample",
                    "to": "/sample/fetch",
                },
                {
                    "title": "Teleport",
                    "to": "/sample/teleport",
                },
                {
                    "title": "Transition",
                    "to": "/sample/transition",
                },
                {
                    "title": "UI Form Controls",
                    "to": "/sample/ui-form-controls",
                },
            ],
        },
    ]
    return html.DIV(
        {},
        DocsNavbar(pages),
        html.MAIN(
            {},
            html.ARTICLE(
                {},
                RouterView(),
            ),
        ),
    )
