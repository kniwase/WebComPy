from __future__ import annotations

from webcompy.ports._dom import DOMEvent
from webcompy.ports._server._virtual_dom import VirtualDOMNode


class FakeDOMNode(VirtualDOMNode):
    def __init__(self, tag: str = "div", text_content: str | None = None):
        super().__init__(tag, node_type=3 if tag.startswith("#text") else 1, text_content=text_content)
        self.__webcompy_prerendered_node__: bool = False
        self.textContent_write_count: int = 0
        self.setAttribute_count: int = 0

    def setAttribute(self, name: str, value: str | None) -> None:
        super().setAttribute(name, value)
        self.setAttribute_count += 1

    @VirtualDOMNode.textContent.setter  # type: ignore[attr-defined]
    def textContent(self, value: str | None) -> None:
        VirtualDOMNode.textContent.fset(self, value)  # type: ignore[misc]
        self.textContent_write_count += 1

    def dispatchEvent(self, event: DOMEvent) -> bool:
        return super().dispatchEvent(event)

    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("_VirtualDOMNode__") or name in (
            "__webcompy_node__",
            "__webcompy_prerendered_node__",
        ):
            object.__setattr__(self, name, value)
        else:
            try:
                object.__getattribute__(self, name)
                object.__setattr__(self, name, value)
            except AttributeError:
                object.__setattr__(self, name, value)

    def __getattr__(self, name: str) -> object:
        if name.startswith("_VirtualDOMNode__"):
            raise AttributeError(name)
        return object.__getattribute__(self, name)
