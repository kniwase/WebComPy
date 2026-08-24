"""DOM node/event protocols and the DOMPort element-creation surface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from typing import Any, Protocol


class DOMEvent(Protocol):
    """Event abstraction mirroring the read-only surface of a native DOM event.

    Attributes:
        bubbles: Whether the event bubbles up through the DOM tree.
        cancelable: Whether the event can be canceled via
            ``preventDefault()``.
        currentTarget: Node whose listener is currently processing the
            event.
        defaultPrevented: Whether ``preventDefault()`` has already been
            called.
        eventPhase: Numeric phase the event flow is in (capturing, at
            target, or bubbling).
        target: Node the event was originally dispatched to, or ``None``.
        timeStamp: Time (in milliseconds) at which the event was created.
        type: Event type name (e.g. ``"click"``).

    """

    def __getattr__(self, _: str) -> Any: ...
    def __setattr__(self, _: str, __: Any) -> None: ...

    @property
    def bubbles(self) -> bool:
        """Whether the event bubbles up through the DOM tree."""
        ...

    @property
    def cancelable(self) -> bool:
        """Whether the event can be canceled via ``preventDefault()``."""
        ...

    @property
    def currentTarget(self) -> DOMNode | None:
        """Node whose listener is currently processing the event."""

    @property
    def defaultPrevented(self) -> bool:
        """Whether ``preventDefault()`` has already been called."""
        ...

    @property
    def eventPhase(self) -> int:
        """Numeric phase the event flow is in (capturing, at target, or bubbling)."""
        ...

    @property
    def target(self) -> DOMNode | None:
        """Node the event was originally dispatched to."""

    @property
    def timeStamp(self) -> int:
        """Time (in milliseconds) at which the event was created."""
        ...

    @property
    def type(self) -> str:
        """Event type name (e.g. ``"click"``)."""
        ...

    def preventDefault(self) -> None:
        """Cancel the event if it is cancelable."""

    def stopPropagation(self) -> None:
        """Prevent further propagation of the event in the DOM tree."""


class DOMNode(Protocol):
    """Node abstraction mirroring the DOM interfaces the framework consumes.

    Attributes:
        __webcompy_node__: Marker flag identifying nodes created by the
            virtual DOM layer.
        __webcompy_prerendered_node__: Marker flag identifying nodes
            adopted from pre-rendered (SSG/SSR) markup.

    """

    def __getattr__(self, name: str) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...

    @property
    def __webcompy_node__(self) -> bool: ...
    @__webcompy_node__.setter
    def __webcompy_node__(self, value: bool) -> None: ...

    @property
    def __webcompy_prerendered_node__(self) -> bool: ...
    @__webcompy_prerendered_node__.setter
    def __webcompy_prerendered_node__(self, value: bool) -> None: ...

    def appendChild(self, child: DOMNode) -> None:
        """Append ``child`` as the last child of this node.

        Args:
            child: Node to append.

        """

    def removeChild(self, child: DOMNode) -> None:
        """Remove ``child`` from this node's children.

        Args:
            child: Child node to remove.

        """

    def insertBefore(self, new_node: DOMNode, ref_node: DOMNode) -> None:
        """Insert ``new_node`` immediately before ``ref_node``.

        Args:
            new_node: Node to insert.
            ref_node: Reference node the new node is inserted before.

        """

    def replaceChild(self, new_node: DOMNode, old_node: DOMNode) -> None:
        """Replace ``old_node`` with ``new_node``.

        Args:
            new_node: Replacement node.
            old_node: Node being replaced.

        """

    def remove(self) -> None:
        """Remove this node from its parent."""

    def setAttribute(self, name: str, value: str | None) -> None:
        """Set an attribute on this node (``None`` removes it).

        Args:
            name: Attribute name.
            value: Attribute value, or ``None`` to remove the attribute.

        """

    def getAttribute(self, name: str) -> str | None:
        """Return the value of an attribute.

        Args:
            name: Attribute name.

        Returns:
            The attribute value, or ``None`` if not present.

        """

    def removeAttribute(self, name: str) -> None:
        """Remove an attribute from this node.

        Args:
            name: Attribute name.

        """

    def hasAttribute(self, name: str) -> bool:
        """Return whether the attribute exists on this node.

        Args:
            name: Attribute name.

        Returns:
            ``True`` if the attribute is present.

        """
        ...

    def getAttributeNames(self) -> list[str]:
        """Return the names of all attributes on this node.

        Returns:
            List of attribute names.

        """
        ...

    def addEventListener(
        self,
        event_type: str,
        handler: Any,
        options_or_capture: Any = False,
    ) -> None:
        """Register an event listener on this node.

        Args:
            event_type: Event type name (e.g. ``"click"``).
            handler: Callback invoked when the event fires.
            options_or_capture: Listener options object or capture boolean
                (default ``False``).

        """

    def removeEventListener(
        self,
        event_type: str,
        handler: Any,
        options_or_capture: Any = False,
    ) -> None:
        """Remove a previously registered event listener.

        Args:
            event_type: Event type name the listener was registered for.
            handler: The callback to remove.
            options_or_capture: Listener options object or capture boolean
                used at registration.

        """

    def dispatchEvent(self, event: DOMEvent) -> bool:
        """Dispatch an event on this node.

        Args:
            event: Event to dispatch.

        Returns:
            ``False`` if the event was canceled via ``preventDefault()``.

        """
        ...

    @property
    def textContent(self) -> str | None:
        """Text content of this node and its descendants."""

    @textContent.setter
    def textContent(self, value: str | None) -> None: ...

    @property
    def childNodes(self) -> DOMNodeList:
        """Live list of this node's child nodes."""
        ...

    @property
    def parentNode(self) -> DOMNode | None:
        """Parent node of this node, or ``None`` if it has no parent."""

    @property
    def nodeName(self) -> str:
        """Name of this node (e.g. the tag name of an element)."""
        ...

    @property
    def nodeType(self) -> int:
        """Numeric node type constant of this node."""
        ...


class DOMNodeList:
    """Immutable sequence wrapper over child DOM nodes.

    Args:
        nodes: The child nodes, in document order.

    Attributes:
        length: Number of nodes in the list.

    """

    def __init__(self, nodes: list[DOMNode]) -> None:
        self._nodes = nodes

    @property
    def length(self) -> int:
        """Number of nodes in the list."""
        return len(self._nodes)

    def __getitem__(self, index: int) -> DOMNode:
        return self._nodes[index]

    def __iter__(self) -> Iterator[DOMNode]:
        return iter(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)


class DOMPort(ABC):
    """DOM element construction and document-query surface.

    Implementations create real or virtual DOM nodes: the browser port
    returns live PyScript element proxies, the server port builds virtual
    DOM trees.
    """

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
    def create_comment(self, data: str) -> DOMNode:
        """Create a comment node.

        Args:
            data: Comment data. Callers must supply comment-safe data (no ``--`` sequence).

        Returns:
            A new comment node.

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
