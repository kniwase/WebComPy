"""Server-side custom element port."""

from __future__ import annotations

from collections.abc import Callable

from webcompy.ports._custom_element import CustomElementBinding, CustomElementPort
from webcompy.ports._dom import DOMNode


class _ServerCustomElementBinding(CustomElementBinding):
    def dispose(self) -> None:
        pass


class ServerCustomElementPort(CustomElementPort):
    """Server-side no-op custom element port."""

    def ensure_defined(
        self,
        name: str,
        observed_attributes: tuple[str, ...],
        definition_key: str,
    ) -> None:
        """Ensure a custom element definition is registered.

        Args:
            name: Tag name of the custom element.
            observed_attributes: Attributes to observe.
            definition_key: Deduplication key for the definition.

        Returns:
            ``None``.

        """
        pass

    def bind(
        self,
        node: DOMNode,
        *,
        observed_attributes: tuple[str, ...],
        on_connected: Callable[[], None],
        on_disconnected: Callable[[], None],
        on_attribute_changed: Callable[[str, str | None], None],
    ) -> CustomElementBinding:
        """Bind lifecycle callbacks to ``node``.

        Args:
            node: DOM node to bind.
            observed_attributes: Attributes to observe.
            on_connected: Callback when the element connects.
            on_disconnected: Callback when the element disconnects.
            on_attribute_changed: Callback for attribute changes.

        Returns:
            Binding handle whose ``dispose`` disconnects the callbacks.

        """
        return _ServerCustomElementBinding()

    def is_document_connected(self, node: DOMNode) -> bool:
        """Return whether ``node`` is connected to the document.

        Args:
            node: Node to check.

        Returns:
            ``False`` on the server.

        """
        return False
