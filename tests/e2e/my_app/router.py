from webcompy.router import Router

from .pages.async_nav import AsyncNavPage
from .pages.classstyle import ClassStylePage
from .pages.component import FunctionStylePage
from .pages.di_test import DiInjectPage, DiProviderWrapper
from .pages.dict_repeat import DictRepeatPage
from .pages.event import EventPage
from .pages.home import HomePage
from .pages.keyed_repeat import KeyedRepeatPage
from .pages.lifecycle import LifecyclePage
from .pages.nested_dynamic import NestedDynamicPage
from .pages.not_found import NotFound
from .pages.repeat import RepeatPage
from .pages.scoped_style import ScopedStylePage
from .pages.signal import ReactivePage
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
    {"path": "/dict-repeat", "component": DictRepeatPage},
    {"path": "/nested-dynamic", "component": NestedDynamicPage},
    {"path": "/lifecycle", "component": LifecyclePage},
    {"path": "/scoped-style", "component": ScopedStylePage},
    {"path": "/async-nav", "component": AsyncNavPage},
    {"path": "/di-provide", "component": DiProviderWrapper},
    {"path": "/di-inject", "component": DiInjectPage},
    default=NotFound,
    mode="history",
    base_url="",
)
