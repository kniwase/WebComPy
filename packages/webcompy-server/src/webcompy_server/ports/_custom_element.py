from __future__ import annotations

from collections.abc import Callable

from webcompy.ports._custom_element import CustomElementBinding, CustomElementPort
from webcompy.ports._dom import DOMNode


class _ServerCustomElementBinding(CustomElementBinding):
    def dispose(self) -> None:
        pass


class ServerCustomElementPort(CustomElementPort):
    def ensure_defined(
        self,
        name: str,
        observed_attributes: tuple[str, ...],
        definition_key: str,
    ) -> None:
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
        return _ServerCustomElementBinding()

    def is_document_connected(self, node: DOMNode) -> bool:
        return False
