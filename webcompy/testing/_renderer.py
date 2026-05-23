from __future__ import annotations

from typing import TYPE_CHECKING

from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.ports._keys import DOM_PORT_KEY, FETCH_PORT_KEY, FFI_PORT_KEY, HOST_PORT_KEY
from webcompy.ports._server._virtual_dom import VirtualDOMNode
from webcompy.testing._asgi import format_html
from webcompy.testing._ports import (
    FakeBrowserDOMPort,
    FakeBrowserFFIPort,
    FakeBrowserHostPort,
    FakeFetchPort,
)

if TYPE_CHECKING:
    from webcompy.components._generator import ComponentGenerator


class TestRendererResult:
    __slots__ = ("_component", "_instance", "_parent_node", "_scope_token")

    def __init__(
        self,
        component: ComponentGenerator,
        instance: object,
        parent_node: VirtualDOMNode,
        scope_token: object,
    ) -> None:
        self._component = component
        self._instance = instance
        self._parent_node = parent_node
        self._scope_token = scope_token

    @property
    def _root_node(self) -> VirtualDOMNode:
        return self._parent_node.childNodes[0] if self._parent_node.childNodes.length > 0 else self._parent_node  # type: ignore[return-value]

    def query_selector(self, tag: str) -> VirtualDOMNode | None:
        return _dfs_first(self._root_node, tag)

    def query_selector_all(self, tag: str) -> list[VirtualDOMNode]:
        return _dfs_all(self._root_node, tag)

    def find_by_text(self, text: str) -> VirtualDOMNode | None:
        return _dfs_text(self._root_node, text)

    def find_by_attribute(self, name: str, value: str) -> VirtualDOMNode | None:
        return _dfs_attr(self._root_node, name, value)

    def to_html(self, *, pretty: bool = False) -> str:
        from webcompy.ports._server._dom import ServerDOMPort

        server_port = ServerDOMPort()
        html = server_port.render_html(self._root_node)
        if pretty:
            return format_html(html)
        return html

    def assert_element_count(self, tag: str, count: int) -> None:
        actual = len(self.query_selector_all(tag))
        assert actual == count, f"Expected {count} <{tag}> elements, found {actual}"

    def assert_has_class(self, cls: str) -> None:
        class_attr = self._root_node.getAttribute("class")
        assert class_attr is not None and cls in class_attr.split(), f"Root element does not have class '{cls}'"

    def close(self) -> None:
        _active_di_scope.reset(self._scope_token)  # type: ignore[arg-type]


class TestRenderer:
    @staticmethod
    def render(component: ComponentGenerator, *, parent_scope: DIScope | None = None) -> TestRendererResult:
        from webcompy.components._component import HeadPropsStore
        from webcompy.di._keys import _HEAD_PROPS_KEY

        scope = DIScope(parent=parent_scope)
        scope.provide(DOM_PORT_KEY, FakeBrowserDOMPort())
        scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
        scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
        scope.provide(FETCH_PORT_KEY, FakeFetchPort())
        scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())

        scope_token = _active_di_scope.set(scope)

        root_node = VirtualDOMNode("div")
        root_node.__webcompy_node__ = False
        root_node.__webcompy_prerendered_node__ = True

        class _DummyParent:
            def __init__(self, node):
                self._node = node

            def _get_node(self):
                return self._node

            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

            def _re_index_children(self, recursive):
                pass

        instance = component(None)
        instance._parent = _DummyParent(root_node)
        instance._node_idx = 0
        instance._render()

        return TestRendererResult(component, instance, root_node, scope_token)


def _dfs_first(node: VirtualDOMNode, tag: str) -> VirtualDOMNode | None:
    tag_upper = tag.upper()
    if node.nodeName == tag_upper:
        return node
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if isinstance(child, VirtualDOMNode):
            result = _dfs_first(child, tag)
            if result is not None:
                return result
    return None


def _dfs_all(node: VirtualDOMNode, tag: str) -> list[VirtualDOMNode]:
    results: list[VirtualDOMNode] = []
    tag_upper = tag.upper()
    if node.nodeName == tag_upper:
        results.append(node)
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if isinstance(child, VirtualDOMNode):
            results.extend(_dfs_all(child, tag))
    return results


def _dfs_text(node: VirtualDOMNode, text: str) -> VirtualDOMNode | None:
    if node.textContent == text:
        return node
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if isinstance(child, VirtualDOMNode):
            result = _dfs_text(child, text)
            if result is not None:
                return result
    return None


def _dfs_attr(node: VirtualDOMNode, name: str, value: str) -> VirtualDOMNode | None:
    if node.getAttribute(name) == value:
        return node
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if isinstance(child, VirtualDOMNode):
            result = _dfs_attr(child, name, value)
            if result is not None:
                return result
    return None
