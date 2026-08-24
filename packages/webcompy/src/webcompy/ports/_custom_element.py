"""Custom-element registration and per-node reaction binding port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Protocol

from webcompy.ports._dom import DOMNode


class CustomElementBinding(Protocol):
    """Handle for a bound custom-element node.

    The binding owns the FFI proxies that forward native custom-element
    reactions to Python. ``dispose()`` releases those proxies and detaches
    the binding from the node.
    """

    def dispose(self) -> None: ...


class CustomElementPort(ABC):
    """Port for custom-element registration and per-node binding.

    The browser implementation defines ``HTMLElement`` subclasses and
    forwards lifecycle and attribute reactions to the callables supplied at
    ``bind()`` time. Server and testing implementations no-op or record
    instead.
    """

    @abstractmethod
    def ensure_defined(
        self,
        name: str,
        observed_attributes: tuple[str, ...],
        definition_key: str,
    ) -> None:
        """Ensure ``name`` is defined in the document's custom-element registry.

        A compatible WebComPy definition (matching ``definition_key``) is
        reused; an incompatible or foreign definition raises
        :class:`WebComPyComponentException`. This SHALL be called before a
        named component creates or adopts its DOM node.

        Args:
            name: Custom element name to define.
            observed_attributes: Attribute names observed by the generated
                element class and forwarded to bound reactions.
            definition_key: Key identifying the WebComPy definition, used
                to detect incompatible redefinitions.

        """
        ...

    @abstractmethod
    def bind(
        self,
        node: DOMNode,
        *,
        observed_attributes: tuple[str, ...],
        on_connected: Callable[[], None],
        on_disconnected: Callable[[], None],
        on_attribute_changed: Callable[[str, str | None], None],
    ) -> CustomElementBinding:
        """Bind a node to custom-element reaction callbacks.

        Reactions are delivered for events that occur after binding. Initial
        connection state is inspected separately via
        :meth:`is_document_connected` so callers can synchronize a node that
        was already connected before binding (e.g. SSR upgrade).

        Args:
            node: DOM node to bind.
            observed_attributes: Attribute names whose changes are reported
                through ``on_attribute_changed``.
            on_connected: Called when the node becomes connected.
            on_disconnected: Called when the node is disconnected.
            on_attribute_changed: Called with ``(attribute_name,
                new_value)``; ``new_value`` is ``None`` when the attribute
                was removed.

        Returns:
            A ``CustomElementBinding`` handle that releases the FFI proxies
            on ``dispose()``.

        """
        ...

    @abstractmethod
    def is_document_connected(self, node: DOMNode) -> bool:
        """Return whether ``node`` is currently connected to a document.

        Args:
            node: DOM node to inspect.

        Returns:
            True if ``node`` is connected to a document, False otherwise.

        """
        ...
