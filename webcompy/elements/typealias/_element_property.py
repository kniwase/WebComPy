from typing import (
    Any,
    Callable,
    Coroutine,
    TypeAlias,
    Union,
)
from webcompy.reactive._base import ReactiveBase
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements._dom_objs import DOMEvent

ElementChildren: TypeAlias = Union[ElementAbstract, ReactiveBase[Any], str, None]
AttrValue: TypeAlias = Union[ReactiveBase[Any], str, int, bool]
EventHandler: TypeAlias = Union[
    Callable[[DOMEvent], Any],
    Callable[[DOMEvent], Coroutine[Any, Any, Any]],
]
