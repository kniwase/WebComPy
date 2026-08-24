"""Test renderer for mounting WebComPy components in a fake DOM."""

from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING

from webcompy import logging
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.ports._keys import (
    ASYNC_SCHEDULER_PORT_KEY,
    CUSTOM_ELEMENT_PORT_KEY,
    DOM_PORT_KEY,
    EVENT_SOURCE_PORT_KEY,
    FFI_PORT_KEY,
    HOST_PORT_KEY,
    MEDIA_QUERY_PORT_KEY,
    TRANSITION_PORT_KEY,
    WEBSOCKET_PORT_KEY,
)
from webcompy_server.ports import VirtualDOMNode
from webcompy_testing._asgi import format_html
from webcompy_testing._ports import (
    FakeAsyncSchedulerPort,
    FakeBrowserDOMPort,
    FakeBrowserFFIPort,
    FakeBrowserHostPort,
    FakeCustomElementPort,
    FakeEventSourcePort,
    FakeMediaQueryPort,
    FakeTransitionPort,
    FakeWebSocketPort,
)
from webcompy_testing._utils import run_sync

if TYPE_CHECKING:
    from webcompy.components._generator import ComponentGenerator


class TestRendererResult:
    """Hold the rendered component tree and its DI scope.

    Provides query helpers and accessors for fake ports installed during
    rendering.

    Args:
        component: Component generator that was rendered.
        instance: Root component instance.
        parent_node: Virtual DOM parent node containing the mounted tree.
        scope: DI scope used for the render.
        di_token: Token for resetting the active DI scope, or ``None``.

    Attributes:
        body_node: Fake document body node, or ``None`` when no fake DOM
            port is installed.
        transition_port: ``FakeTransitionPort`` installed for the render,
            or ``None``.
        media_query_port: ``FakeMediaQueryPort`` installed for the
            render, or ``None``.
        event_source_port: ``FakeEventSourcePort`` installed for the
            render, or ``None``.
        websocket_port: ``FakeWebSocketPort`` installed for the render,
            or ``None``.

    """

    __slots__ = ("_component", "_di_token", "_instance", "_parent_node", "_scope")

    def __init__(
        self,
        component: ComponentGenerator,
        instance: object,
        parent_node: VirtualDOMNode,
        scope: DIScope,
        di_token: contextvars.Token | None = None,
    ) -> None:
        self._component = component
        self._instance = instance
        self._parent_node = parent_node
        self._scope = scope
        self._di_token = di_token

    @property
    def _root_node(self) -> VirtualDOMNode:
        return self._parent_node.childNodes[0] if self._parent_node.childNodes.length > 0 else self._parent_node  # type: ignore[return-value]

    def query_selector(self, tag: str) -> VirtualDOMNode | None:
        """Return the first node with the given tag.

        Args:
            tag: Tag name to search for.

        Returns:
            The first matching node or ``None``.

        """
        return _dfs_first(self._root_node, tag)

    def query_selector_all(self, tag: str) -> list[VirtualDOMNode]:
        """Return all nodes with the given tag.

        Args:
            tag: Tag name to search for.

        Returns:
            List of matching nodes.

        """
        return _dfs_all(self._root_node, tag)

    def find_by_text(self, text: str) -> VirtualDOMNode | None:
        """Find a node by exact text content.

        Args:
            text: Text to match against ``textContent``.

        Returns:
            The first matching node or ``None``.

        """
        return _dfs_text(self._root_node, text)

    def find_by_attribute(self, name: str, value: str) -> VirtualDOMNode | None:
        """Find a node by attribute value.

        Args:
            name: Attribute name.
            value: Expected attribute value.

        Returns:
            The first matching node or ``None``.

        """
        return _dfs_attr(self._root_node, name, value)

    def to_html(self, *, pretty: bool = False) -> str:
        """Render the mounted tree to an HTML string.

        Args:
            pretty: Whether to pretty-print the HTML.

        Returns:
            HTML string for the mounted component tree.

        """
        from webcompy_server.ports._dom import ServerDOMPort

        server_port = ServerDOMPort()
        html = server_port.render_html(self._root_node)
        if pretty:
            return format_html(html)
        return html

    def assert_element_count(self, tag: str, count: int) -> None:
        """Assert that ``count`` elements with ``tag`` exist.

        Args:
            tag: Tag name to count.
            count: Expected number of elements.

        """
        actual = len(self.query_selector_all(tag))
        assert actual == count, f"Expected {count} <{tag}> elements, found {actual}"

    def assert_has_class(self, cls: str) -> None:
        """Assert that the root element contains a CSS class.

        Args:
            cls: Class name expected on the root element.

        """
        class_attr = self._root_node.getAttribute("class")
        assert class_attr is not None and cls in class_attr.split(), f"Root element does not have class '{cls}'"

    def __enter__(self) -> TestRendererResult:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Dispose the DI scope and reset the active scope token."""
        self._scope.dispose()
        if self._di_token is not None:
            try:
                _active_di_scope.reset(self._di_token)
            except (ValueError, LookupError) as err:
                logging.warning(
                    "TestRendererResult.close() called from a different context "
                    "than render(); DI scope token cannot be reset: %s",
                    err,
                )

    @property
    def body_node(self) -> VirtualDOMNode | None:
        """Return the fake document body node."""
        dom = self._scope.inject(DOM_PORT_KEY, default=None)
        if isinstance(dom, FakeBrowserDOMPort):
            return dom.body
        return None

    @property
    def transition_port(self) -> FakeTransitionPort | None:
        """Return the ``FakeTransitionPort`` installed for the render."""
        return self._scope.inject(TRANSITION_PORT_KEY, default=None)

    @property
    def media_query_port(self) -> FakeMediaQueryPort | None:
        """Return the ``FakeMediaQueryPort`` installed for the render."""
        return self._scope.inject(MEDIA_QUERY_PORT_KEY, default=None)

    @property
    def event_source_port(self) -> FakeEventSourcePort | None:
        """Return the ``FakeEventSourcePort`` installed for the render."""
        return self._scope.inject(EVENT_SOURCE_PORT_KEY, default=None)

    @property
    def websocket_port(self) -> FakeWebSocketPort | None:
        """Return the ``FakeWebSocketPort`` installed for the render."""
        return self._scope.inject(WEBSOCKET_PORT_KEY, default=None)


class TestRenderer:
    """Mount WebComPy components into a fake DOM for assertions."""

    @staticmethod
    def render(
        component: ComponentGenerator,
        *,
        parent_scope: DIScope | None = None,
    ) -> TestRendererResult:
        """Render a component into an isolated fake DOM.

        Args:
            component: Component generator to mount.
            parent_scope: Optional parent DI scope for the render.

        Returns:
            A ``TestRendererResult`` holding the mounted tree and scopes.

        """

        async def _render_async() -> tuple[object, VirtualDOMNode, DIScope]:
            from webcompy.components._component import HeadPropsStore
            from webcompy.components._generator import (
                ComponentStore,
                _register_deferred_components,
            )
            from webcompy.di._keys import (
                _COMPONENT_STORE_KEY,
                _HEAD_PROPS_KEY,
                _TELEPORT_REGISTRY_KEY,
            )
            from webcompy.elements.types._teleport import _TeleportTargetRegistry

            scope = DIScope(parent=parent_scope)
            fake_scheduler = FakeAsyncSchedulerPort()
            scope.provide(ASYNC_SCHEDULER_PORT_KEY, fake_scheduler)
            dom_port = FakeBrowserDOMPort()
            scope.provide(DOM_PORT_KEY, dom_port)
            scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
            scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
            scope.provide(CUSTOM_ELEMENT_PORT_KEY, FakeCustomElementPort())
            scope.provide(EVENT_SOURCE_PORT_KEY, FakeEventSourcePort())
            scope.provide(TRANSITION_PORT_KEY, FakeTransitionPort())
            scope.provide(MEDIA_QUERY_PORT_KEY, FakeMediaQueryPort())
            scope.provide(WEBSOCKET_PORT_KEY, FakeWebSocketPort())
            scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
            scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
            scope.provide(_TELEPORT_REGISTRY_KEY, _TeleportTargetRegistry())

            _active_di_scope.set(scope)
            _register_deferred_components()

            root_node = VirtualDOMNode("div")
            root_node.__webcompy_node__ = False
            root_node.__webcompy_prerendered_node__ = True
            dom_port._body.appendChild(root_node)

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
            instance._parent = _DummyParent(root_node)  # type: ignore[assignment]
            instance._node_idx = 0
            await instance._render()
            await fake_scheduler.await_pending()

            return instance, root_node, scope

        ctx = contextvars.copy_context()
        instance, root_node, scope = ctx.run(run_sync, _render_async())
        di_token = _active_di_scope.set(scope)
        return TestRendererResult(component, instance, root_node, scope, di_token)


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
    if node.nodeType != 8 and node.textContent == text:
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
