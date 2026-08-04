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

    def splitText(self, offset: int) -> FakeDOMNode:
        if self._node_type != 3:
            raise TypeError("splitText is only valid on text nodes")
        text = self._text_content or ""
        if not 0 <= offset <= len(text):
            raise IndexError(f"splitText offset {offset} out of range for text of length {len(text)}")
        new_node = FakeDOMNode("#text", text_content=text[offset:])
        self._text_content = text[:offset]
        parent = self._parent
        if parent is not None:
            siblings = parent._children
            idx = siblings.index(self)
            if idx + 1 < len(siblings):
                parent.insertBefore(new_node, siblings[idx + 1])
            else:
                parent.appendChild(new_node)
        return new_node

    @VirtualDOMNode.textContent.setter  # type: ignore[attr-defined]
    def textContent(self, value: str | None) -> None:
        VirtualDOMNode.textContent.fset(self, value)  # type: ignore[misc]
        self.textContent_write_count += 1

    def __setattr__(self, name: str, value: object) -> None:
        if name == "__webcompy_prerendered_node__" and value:
            object.__setattr__(self, "_webcompy_node", False)
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
