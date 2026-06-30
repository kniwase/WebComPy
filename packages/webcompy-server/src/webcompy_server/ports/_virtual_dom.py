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
        self._dom_properties: dict[str, Any] = {}
        self._innerHTML: str | None = None

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
        if self._node_type == 1:
            parts: list[str] = []
            for child in self._children:
                text = child.textContent
                if text is not None:
                    parts.append(text)
            return "".join(parts) if parts else ""
        return self._text_content

    @textContent.setter
    def textContent(self, value: str | None) -> None:
        if self._node_type == 1:
            self._children.clear()
            if value is not None:
                child = VirtualDOMNode("#text", node_type=3, text_content=value)
                child._parent = self
                self._children.append(child)
        else:
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
        if child not in self._children:
            raise ValueError("Node is not a child of this element")
        self._children.remove(child)
        _as_virtual(child)._parent = None

    def insertBefore(self, new_node: DOMNode, ref_node: DOMNode) -> None:
        new_v = _as_virtual(new_node)
        if new_v._parent is not None:
            new_v._parent.removeChild(new_node)
        if ref_node not in self._children:
            raise ValueError("Reference node is not a child of this element")
        idx = self._children.index(ref_node)
        new_v._parent = self
        self._children.insert(idx, new_node)

    def replaceChild(self, new_node: DOMNode, old_node: DOMNode) -> None:
        new_v = _as_virtual(new_node)
        old_v = _as_virtual(old_node)
        if new_v._parent is not None:
            new_v._parent.removeChild(new_node)
        if old_node not in self._children:
            raise ValueError("Node to replace is not a child of this element")
        idx = self._children.index(old_node)
        self._children[idx] = new_node
        new_v._parent = self
        old_v._parent = None

    def remove(self) -> None:
        if self._parent is not None:
            self._parent.removeChild(self)

    def setAttribute(self, name: str, value: str | None) -> None:
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
        # VirtualDOMNode and VirtualDOMEvent live in the same module, so
        # we directly access the event's private attributes (_target,
        # _propagation_stopped, etc.) to implement DOM-spec event phases.
        event_v = _as_virtual_event(event)
        event_v._target = self
        event_v._current_target = self
        event_v._event_phase = 2
        for et, handler in self._event_listeners:
            if et == event.type:
                handler(event)
        if not event_v._propagation_stopped and event.bubbles:
            event_v._event_phase = 3
            ancestor = self._parent
            while ancestor is not None:
                if event_v._propagation_stopped:
                    break
                ancestor_v = _as_virtual(ancestor)
                event_v._current_target = ancestor
                for et, handler in ancestor_v._event_listeners:
                    if et == event.type:
                        handler(event)
                ancestor = ancestor_v._parent
        event_v._event_phase = 0
        event_v._current_target = None
        return not event_v._default_prevented

    def __getattr__(self, name: str) -> Any:
        if name in self._dom_properties:
            return self._dom_properties[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "innerHTML":
            object.__setattr__(self, "_innerHTML", value)
            return
        if name.startswith("_") or name in {
            "nodeName",
            "nodeType",
            "textContent",
            "childNodes",
            "firstChild",
            "lastChild",
            "parentNode",
            "attributes",
            "innerHTML",
            "outerHTML",
        }:
            object.__setattr__(self, name, value)
        else:
            self._dom_properties[name] = value

    def __getattribute__(self, name: str) -> Any:
        if name == "innerHTML":
            return object.__getattribute__(self, "_innerHTML")
        return object.__getattribute__(self, name)


def _as_virtual(node: DOMNode) -> VirtualDOMNode:
    if not isinstance(node, VirtualDOMNode):
        raise TypeError(f"Expected VirtualDOMNode, got {type(node).__name__}")
    return node


def _as_virtual_event(event: DOMEvent) -> VirtualDOMEvent:
    if not isinstance(event, VirtualDOMEvent):
        raise TypeError(f"Expected VirtualDOMEvent, got {type(event).__name__}")
    return event
