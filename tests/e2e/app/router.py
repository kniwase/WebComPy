from webcompy.router import Router

from .pages.async_nav import AsyncNavPage
from .pages.classstyle import ClassStylePage
from .pages.component import FunctionStylePage
from .pages.event import EventPage
from .pages.home import HomePage
from .pages.keyed_repeat import KeyedRepeatPage
from .pages.lifecycle import LifecyclePage
from .pages.not_found import NotFound
from .pages.reactive import ReactivePage
from .pages.repeat import RepeatPage
from .pages.scoped_style import ScopedStylePage
from .pages.switch_test import SwitchPage

router = Router(
    {"path": "/", "component": HomePage},
    {"path": "/reactive", "component": ReactivePage},
    {"path": "/component", "component": FunctionStylePage},
    {"path": "/component/classstyle", "component": ClassStylePage},
    {"path": "/event", "component": EventPage},
    {"path": "/switch", "component": SwitchPage},
    {"path": "/repeat", "component": RepeatPage},
    {"path": "/keyed-repeat", "component": KeyedRepeatPage},
    {"path": "/lifecycle", "component": LifecyclePage},
    {"path": "/scoped-style", "component": ScopedStylePage},
    {"path": "/async-nav", "component": AsyncNavPage},
    default=NotFound,
    mode="history",
    base_url="",
)
