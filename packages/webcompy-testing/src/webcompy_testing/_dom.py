from __future__ import annotations

from webcompy_server.ports import VirtualDOMNode


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

    def __setattr__(self, name: str, value: object) -> None:
        if (
            name.startswith("_VirtualDOMNode__")
            or name in ("__webcompy_node__", "__webcompy_prerendered_node__")
            or name in ("textContent_write_count", "setAttribute_count")
            or name
            in {
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
            }
            or name.startswith("_")
        ):
            object.__setattr__(self, name, value)
        else:
            super().__setattr__(name, value)

    def __getattribute__(self, name: str) -> object:
        if name == "innerHTML":
            try:
                return object.__getattribute__(self, "_innerHTML")
            except AttributeError:
                return None
        return object.__getattribute__(self, name)

    def __getattr__(self, name: str) -> object:
        if name.startswith("_VirtualDOMNode__"):
            raise AttributeError(name)
        try:
            return self._dom_properties[name]
        except KeyError:
            return object.__getattribute__(self, name)
