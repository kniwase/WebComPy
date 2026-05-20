from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from webcompy.ports._dom import DOMEvent, DOMNode, DOMNodeList


class VirtualDOMEvent:
    def __init__(
        self,
        event_type: str,
        *,
        bubbles: bool = False,
        cancelable: bool = False,
    ) -> None:
        self._type: str = event_type
        self._bubbles: bool = bubbles
        self._cancelable: bool = cancelable
        self._default_prevented: bool = False
        self._event_phase: int = 0
        self._target: DOMNode | None = None
        self._current_target: DOMNode | None = None
        self._time_stamp: int = int(time.time() * 1000)
        self._propagation_stopped: bool = False

    @property
    def type(self) -> str:
        return self._type

    @property
    def bubbles(self) -> bool:
        return self._bubbles

    @property
    def cancelable(self) -> bool:
        return self._cancelable

    @property
    def target(self) -> DOMNode | None:
        return self._target

    @property
    def currentTarget(self) -> DOMNode | None:
        return self._current_target

    @property
    def defaultPrevented(self) -> bool:
        return self._default_prevented

    @property
    def eventPhase(self) -> int:
        return self._event_phase

    @property
    def timeStamp(self) -> int:
        return self._time_stamp

    def preventDefault(self) -> None:
        if self._cancelable:
            self._default_prevented = True

    def stopPropagation(self) -> None:
        self._propagation_stopped = True

    def __getattr__(self, _: str) -> Any:
        return None


class VirtualDOMNode:
    def __init__(
        self,
        tag_name: str,
        *,
        node_type: int = 1,
        text_content: str | None = None,
    ) -> None:
        self._tag_name: str = tag_name
        self._node_type: int = node_type
        self._text_content: str | None = text_content
        self._attributes: dict[str, str | None] = {}
        self._children: list[DOMNode] = []
        self._event_listeners: list[tuple[str, Callable[..., Any]]] = []
        self._parent: DOMNode | None = None
        self._webcompy_node: bool = True
        self._webcompy_prerendered_node: bool = False

    @property
    def __webcompy_node__(self) -> bool:
        return self._webcompy_node

    @__webcompy_node__.setter
    def __webcompy_node__(self, value: bool) -> None:
        self._webcompy_node = value

    @property
    def __webcompy_prerendered_node__(self) -> bool:
        return self._webcompy_prerendered_node

    @__webcompy_prerendered_node__.setter
    def __webcompy_prerendered_node__(self, value: bool) -> None:
        self._webcompy_prerendered_node = value

    @property
    def nodeName(self) -> str:
        if self._node_type == 3:
            return "#text"
        return self._tag_name.upper()

    @property
    def nodeType(self) -> int:
        return self._node_type

    @property
    def textContent(self) -> str | None:
        return self._text_content

    @textContent.setter
    def textContent(self, value: str | None) -> None:
        self._text_content = value

    @property
    def childNodes(self) -> DOMNodeList:
        return DOMNodeList(self._children)

    @property
    def parentNode(self) -> DOMNode | None:
        return self._parent

    def appendChild(self, child: DOMNode) -> None:
        child_v = _as_virtual(child)
        if child_v._parent is not None:
            child_v._parent.removeChild(child)
        child_v._parent = self
        self._children.append(child)

    def removeChild(self, child: DOMNode) -> None:
        self._children.remove(child)
        _as_virtual(child)._parent = None

    def insertBefore(self, new_node: DOMNode, ref_node: DOMNode) -> None:
        new_v = _as_virtual(new_node)
        if new_v._parent is not None:
            new_v._parent.removeChild(new_node)
        idx = self._children.index(ref_node)
        new_v._parent = self
        self._children.insert(idx, new_node)

    def replaceChild(self, new_node: DOMNode, old_node: DOMNode) -> None:
        new_v = _as_virtual(new_node)
        old_v = _as_virtual(old_node)
        if new_v._parent is not None:
            new_v._parent.removeChild(new_node)
        idx = self._children.index(old_node)
        self._children[idx] = new_node
        new_v._parent = self
        old_v._parent = None

    def remove(self) -> None:
        if self._parent is not None:
            self._parent.removeChild(self)

    def setAttribute(self, name: str, value: str) -> None:
        self._attributes[name] = value

    def getAttribute(self, name: str) -> str | None:
        return self._attributes.get(name)

    def removeAttribute(self, name: str) -> None:
        self._attributes.pop(name, None)

    def hasAttribute(self, name: str) -> bool:
        return name in self._attributes

    def getAttributeNames(self) -> list[str]:
        return list(self._attributes.keys())

    def addEventListener(
        self,
        event_type: str,
        handler: Any,
        options_or_capture: Any = False,
    ) -> None:
        self._event_listeners.append((event_type, handler))

    def removeEventListener(
        self,
        event_type: str,
        handler: Any,
        options_or_capture: Any = False,
    ) -> None:
        self._event_listeners = [(et, h) for et, h in self._event_listeners if not (et == event_type and h is handler)]

    def dispatchEvent(self, event: DOMEvent) -> bool:
        event_v = _as_virtual_event(event)
        event_v._target = self
        event_v._current_target = self
        event_v._event_phase = 2
        for et, handler in self._event_listeners:
            if et == event.type and not event_v._propagation_stopped:
                handler(event)
        if event_v._propagation_stopped:
            return not event_v._default_prevented
        if event.bubbles:
            event_v._event_phase = 3
            ancestor = self._parent
            while ancestor is not None:
                ancestor_v = _as_virtual(ancestor)
                event_v._current_target = ancestor
                for et, handler in ancestor_v._event_listeners:
                    if et == event.type and not event_v._propagation_stopped:
                        handler(event)
                if event_v._propagation_stopped:
                    break
                ancestor = ancestor_v._parent
        return not event_v._default_prevented


def _as_virtual(node: DOMNode) -> VirtualDOMNode:
    assert isinstance(node, VirtualDOMNode)
    return node


def _as_virtual_event(event: DOMEvent) -> VirtualDOMEvent:
    assert isinstance(event, VirtualDOMEvent)
    return event
