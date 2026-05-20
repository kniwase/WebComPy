from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from typing import Any, Protocol


class DOMEvent(Protocol):
    def __getattr__(self, _: str) -> Any: ...

    @property
    def bubbles(self) -> bool: ...

    @property
    def cancelable(self) -> bool: ...

    @property
    def currentTarget(self) -> DOMNode | None: ...

    @property
    def defaultPrevented(self) -> bool: ...

    @property
    def eventPhase(self) -> int: ...

    @property
    def target(self) -> DOMNode | None: ...

    @property
    def timeStamp(self) -> int: ...

    @property
    def type(self) -> str: ...

    def preventDefault(self) -> None: ...

    def stopPropagation(self) -> None: ...


class DOMNode(Protocol):
    @property
    def __webcompy_node__(self) -> bool: ...
    @__webcompy_node__.setter
    def __webcompy_node__(self, value: bool) -> None: ...

    @property
    def __webcompy_prerendered_node__(self) -> bool: ...
    @__webcompy_prerendered_node__.setter
    def __webcompy_prerendered_node__(self, value: bool) -> None: ...

    def appendChild(self, child: DOMNode) -> None: ...
    def removeChild(self, child: DOMNode) -> None: ...
    def insertBefore(self, new_node: DOMNode, ref_node: DOMNode) -> None: ...
    def replaceChild(self, new_node: DOMNode, old_node: DOMNode) -> None: ...
    def remove(self) -> None: ...

    def setAttribute(self, name: str, value: str) -> None: ...
    def getAttribute(self, name: str) -> str | None: ...
    def removeAttribute(self, name: str) -> None: ...
    def hasAttribute(self, name: str) -> bool: ...
    def getAttributeNames(self) -> list[str]: ...

    def addEventListener(
        self,
        event_type: str,
        handler: Any,
        options_or_capture: Any = False,
    ) -> None: ...
    def removeEventListener(
        self,
        event_type: str,
        handler: Any,
        options_or_capture: Any = False,
    ) -> None: ...

    def dispatchEvent(self, event: DOMEvent) -> bool: ...

    @property
    def textContent(self) -> str | None: ...

    @textContent.setter
    def textContent(self, value: str | None) -> None: ...

    @property
    def childNodes(self) -> DOMNodeList: ...

    @property
    def parentNode(self) -> DOMNode | None: ...

    @property
    def nodeName(self) -> str: ...

    @property
    def nodeType(self) -> int: ...


class DOMNodeList:
    def __init__(self, nodes: list[DOMNode]) -> None:
        self._nodes = nodes

    @property
    def length(self) -> int:
        return len(self._nodes)

    def __getitem__(self, index: int) -> DOMNode:
        return self._nodes[index]

    def __iter__(self) -> Iterator[DOMNode]:
        return iter(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)


class DOMPort(ABC):
    @abstractmethod
    def create_element(self, tag: str) -> DOMNode:
        """Create an HTML element.

        Args:
            tag: HTML tag name (e.g. ``"div"``, ``"span"``, ``"p"``).

        Returns:
            A new DOM element.
        """
        ...

    @abstractmethod
    def create_text_node(self, text: str) -> DOMNode:
        """Create a text node.

        Args:
            text: Text content for the node.

        Returns:
            A new text node.
        """
        ...

    @abstractmethod
    def query_selector(self, selector: str) -> DOMNode | None:
        """Query the document for the first element matching a CSS selector.

        Args:
            selector: CSS selector string.

        Returns:
            The first matching element, or ``None`` if none found.
        """
        ...

    @abstractmethod
    def get_element_by_id(self, element_id: str) -> DOMNode | None:
        """Retrieve an element by its ``id`` attribute.

        Args:
            element_id: The element's ``id`` value.

        Returns:
            The matching element, or ``None`` if not found.
        """
        ...

    @abstractmethod
    def set_title(self, title: str) -> None:
        """Set the document title (``document.title``).

        Args:
            title: New document title.
        """
        ...

    @abstractmethod
    def add_document_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]:
        """Register a document-level event listener via ``document.addEventListener``.

        Args:
            event_type: Event name (e.g. ``"click"``, ``"keydown"``).
            handler: Callback invoked when the event fires.

        Returns:
            A cleanup function; call it to remove the listener.
        """
        ...

    @abstractmethod
    def create_event(
        self,
        event_type: str,
        *,
        bubbles: bool = False,
        cancelable: bool = False,
    ) -> DOMEvent:
        """Create a DOM event object.

        Args:
            event_type: Event type string (e.g. ``"click"``, ``"submit"``).
            bubbles: Whether the event bubbles up through the DOM.
            cancelable: Whether the event can be canceled via ``preventDefault()``.

        Returns:
            A new DOM event object.
        """
        ...
