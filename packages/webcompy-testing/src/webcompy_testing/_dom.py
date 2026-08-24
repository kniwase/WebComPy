"""Fake DOM node for browserless component testing."""

from __future__ import annotations

from webcompy.elements.types._base import _utf16_length
from webcompy_server.ports import VirtualDOMNode


class FakeDOMNode(VirtualDOMNode):
    """Provide a test double for ``VirtualDOMNode`` with write tracking.

    Args:
        tag: Tag name for the node.
        text_content: Initial text content for text/comment nodes.
        node_type: Explicit DOM node type override.

    Attributes:
        textContent_write_count: Number of times ``textContent`` was
            written on this node.
        setAttribute_count: Number of times ``setAttribute`` was called
            on this node.

    """

    def __init__(self, tag: str = "div", text_content: str | None = None, *, node_type: int | None = None) -> None:
        if node_type is None:
            node_type = 8 if tag.startswith("#comment") else (3 if tag.startswith("#text") else 1)
        super().__init__(tag, node_type=node_type, text_content=text_content)
        self.__webcompy_prerendered_node__: bool = False
        self.textContent_write_count: int = 0
        self.setAttribute_count: int = 0

    def setAttribute(self, name: str, value: str | None) -> None:
        """Assign an attribute and increment the write counter.

        Args:
            name: Attribute name.
            value: Attribute value or ``None`` to remove the attribute.

        """
        super().setAttribute(name, value)
        self.setAttribute_count += 1

    def splitText(self, offset: int) -> FakeDOMNode:
        """Split a text node at a UTF-16 offset and insert the remainder.

        Args:
            offset: UTF-16 code-unit offset at which to split.

        Returns:
            The newly created sibling text node containing the tail.

        Raises:
            TypeError: If the node is not a text node.
            IndexError: If ``offset`` is out of range.

        """
        if self._node_type != 3:
            raise TypeError("splitText is only valid on text nodes")
        text = self._text_content or ""
        length = _utf16_length(text)
        if not 0 <= offset <= length:
            raise IndexError(f"splitText offset {offset} out of range for text of length {length}")
        encoded = text.encode("utf-16-le", "surrogatepass")
        boundary = offset * 2
        new_node = FakeDOMNode(
            "#text",
            text_content=encoded[boundary:].decode("utf-16-le", "surrogatepass"),
        )
        self._text_content = encoded[:boundary].decode("utf-16-le", "surrogatepass")
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
        if name == "innerHTML":
            VirtualDOMNode.__setattr__(self, name, value)
            return
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
