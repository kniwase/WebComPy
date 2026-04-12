from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterView

from .components.navigation import Navbar, Page


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
            "children": [],
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
                    "title": "HelloWorld (ClassStyle)",
                    "to": "/sample/helloworld-classstyle",
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
