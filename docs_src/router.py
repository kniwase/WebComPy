from webcompy.router import Router

from .pages.demo.fetch_sample import FetchSamplePage
from .pages.demo.fizzbuzz import FizzbuzzPage
from .pages.demo.helloworld import HelloWorldPage
from .pages.demo.matplotlib_sample import MatpoltlibSamplePage
from .pages.demo.todo import ToDoListPage
from .pages.document.home import DocumentHomePage
from .pages.home import HomePage
from .pages.not_found import NotFound

router = Router(
    {"path": "/", "component": HomePage},
    {"path": "/documents", "component": DocumentHomePage},
    {"path": "/sample/helloworld", "component": HelloWorldPage},
    {"path": "/sample/fizzbuzz", "component": FizzbuzzPage},
    {"path": "/sample/todo", "component": ToDoListPage},
    {"path": "/sample/matplotlib", "component": MatpoltlibSamplePage},
    {"path": "/sample/fetch", "component": FetchSamplePage},
    default=NotFound,
    mode="history",
    base_url="",
)
