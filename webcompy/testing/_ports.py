from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from webcompy.testing._dom import FakeDOMNode


class FakeBrowserDOMPort:
    def create_element(self, tag: str) -> FakeDOMNode:
        return FakeDOMNode(tag)

    def create_text_node(self, text: str) -> FakeDOMNode:
        return FakeDOMNode("#text", text_content=text)

    def query_selector(self, selector: str) -> FakeDOMNode | None:
        return None

    def get_element_by_id(self, element_id: str) -> FakeDOMNode | None:
        return None

    def set_title(self, title: str) -> None:
        pass

    def add_document_event_listener(self, event_type: str, handler: Any) -> Any:
        return lambda: None

    def create_event(
        self,
        event_type: str,
        *,
        bubbles: bool = False,
        cancelable: bool = False,
    ) -> Any:
        event = MagicMock()
        event.type = event_type
        event.bubbles = bubbles
        event.cancelable = cancelable
        return event


class FakeBrowserHostPort:
    def schedule_macro_task(self, callback: Any) -> None:
        pass

    def create_js_global_getter(
        self,
        name: str,
        *,
        wrapper: Any = None,
        default: Any = None,
    ) -> Any:
        def _getter() -> Any:
            if wrapper is not None:
                return wrapper(None)
            return default

        return _getter


class FakeBrowserFFIPort:
    def create_proxy(self, func: Any) -> Any:
        proxy = MagicMock(side_effect=func)
        proxy.destroy = MagicMock()
        return proxy

    def destroy_proxy(self, proxy: Any) -> None:
        if hasattr(proxy, "destroy"):
            proxy.destroy()

    def is_none(self, value: Any) -> bool:
        return value is None

    def to_js(self, value: Any, **kwargs: Any) -> Any:
        return value

    def assign(self, target: Any, *sources: Any) -> Any:
        for source in sources:
            target.update(source)
        return target
