from collections.abc import Callable, Coroutine
from typing import Any, TypeAlias

from webcompy.elements._dom_objs import DOMEvent
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.reactive._base import ReactiveBase

ElementChildren: TypeAlias = ElementAbstract | ReactiveBase[Any] | str | None
AttrValue: TypeAlias = ReactiveBase[Any] | str | int | bool
EventHandler: TypeAlias = Callable[[DOMEvent], Any] | Callable[[DOMEvent], Coroutine[Any, Any, Any]]
