from collections.abc import Callable, Coroutine
from typing import Any, TypeAlias

from webcompy.elements._dom_objs import DOMEvent
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.signal._base import SignalBase

ElementChildren: TypeAlias = ElementAbstract | SignalBase[Any] | str | None
AttrValue: TypeAlias = SignalBase[Any] | str | int | bool
EventHandler: TypeAlias = Callable[[DOMEvent], Any] | Callable[[DOMEvent], Coroutine[Any, Any, Any]]
