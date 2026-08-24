"""Type aliases describing element attributes, children, and event handlers."""

from collections.abc import Callable, Coroutine
from typing import Any, TypeAlias

from webcompy.elements._dom_objs import DOMEvent
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.signal import SignalBase

ElementChildren: TypeAlias = ElementAbstract | SignalBase[Any] | str | None
"""A child node: an element, a reactive value rendering as text, a plain string, or ``None``."""

AttrValue: TypeAlias = SignalBase[Any] | str | int | bool
"""An attribute value: a plain value or a reactive signal providing one."""

EventHandler: TypeAlias = Callable[[DOMEvent], Any] | Callable[[DOMEvent], Coroutine[Any, Any, Any]]
"""An event listener callback: a synchronous function or a coroutine receiving a ``DOMEvent``."""
