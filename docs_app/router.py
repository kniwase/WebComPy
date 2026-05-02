from webcompy.router import Router, lazy

from .pages.home import HomePage
from .pages.not_found import NotFound

router = Router(
    {"path": "/", "component": HomePage},
    {"path": "/documents", "component": lazy("docs_app.pages.document.home:DocumentHomePage", __file__)},
    {"path": "/sample/helloworld", "component": lazy("docs_app.pages.demo.helloworld:HelloWorldPage", __file__)},
    {"path": "/sample/fizzbuzz", "component": lazy("docs_app.pages.demo.fizzbuzz:FizzbuzzPage", __file__)},
    {"path": "/sample/todo", "component": lazy("docs_app.pages.demo.todo:ToDoListPage", __file__)},
    {
        "path": "/sample/matplotlib",
        "component": lazy("docs_app.pages.demo.matplotlib_sample:MatpoltlibSamplePage", __file__),
    },
    {"path": "/sample/fetch", "component": lazy("docs_app.pages.demo.fetch_sample:FetchSamplePage", __file__)},
    default=NotFound,
    mode="history",
    base_url="",
)
