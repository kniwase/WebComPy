from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterView

from ..components.navigation import Navbar, Page
from ..docs_manifest import flatten_pages


@define_component
def Root(_: ComponentContext[None]):
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
            ],
        },
    ]
    return html.DIV(
        {},
        Navbar(pages),
        html.MAIN(
            {},
            html.ARTICLE(
                {},
                RouterView(),
            ),
        ),
    )
