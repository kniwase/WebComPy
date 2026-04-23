from __future__ import annotations

from abc import abstractmethod
from typing import cast

from webcompy._browser._modules import browser
from webcompy.elements._dom_objs import DOMNode
from webcompy.exception import WebComPyException
from webcompy.signal._base import CallbackConsumerNode
from webcompy.signal._container import SignalReceivable
from webcompy.signal._graph import consumer_destroy


class ElementAbstract(SignalReceivable):
    _node_idx: int
    _node_cache: DOMNode | None = None
    _mounted: bool | None = None
    _remount_to: DOMNode | None = None
    _callback_nodes: list[CallbackConsumerNode]
    __parent: ElementAbstract

    def __init__(self) -> None:
        self._node_cache = None
        self._mounted = None
        self._remount_to = None
        self._callback_nodes: list[CallbackConsumerNode] = []

    @property
    def _parent(self) -> ElementAbstract:
        return self.__parent

    @_parent.setter
    def _parent(self, parent: ElementAbstract):
        self.__parent = parent

    def _render(self):
        self._mount_node()

    def _mount_node(self):
        if not self._mounted and (node := self._get_node()):
            parent_node = self._parent._get_node()
            if self._mounted is None:
                if parent_node.childNodes.length <= self._node_idx:
                    parent_node.appendChild(node)
                else:
                    next_node = parent_node.childNodes[self._node_idx]
                    parent_node.insertBefore(node, next_node)
            elif not self._mounted and self._remount_to:
                parent_node.replaceChild(node, self._remount_to)
                self._remount_to = None
            self._mounted = True

    def _detach_node(self):
        if browser and self._node_cache:
            parent_node = self._parent._get_node()
            self._remount_to = cast("DOMNode", browser.document.createTextNode(""))
            parent_node.replaceChild(self._remount_to, self._node_cache)
            self._mounted = False
        else:
            raise WebComPyException("Not in Browser environment.")

    @abstractmethod
    def _init_node(self) -> DOMNode: ...

    def _hydrate_node(self) -> DOMNode | None:
        existing = self._get_existing_node()
        if (
            existing
            and getattr(existing, "__webcompy_prerendered_node__", False)
            and self._node_matches_existing(existing)
        ):
            self._adopt_node(existing)
            return existing
        else:
            if existing:
                existing.remove()
            return self._init_node()

    def _node_matches_existing(self, existing: DOMNode) -> bool:
        return True

    def _adopt_node(self, node: DOMNode) -> None:
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True

    def _add_callback_node(self, callback_node: CallbackConsumerNode):
        self._callback_nodes.append(callback_node)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        for callback_node in self._callback_nodes:
            consumer_destroy(callback_node)
        if remove_node:
            node = self._get_node()
            if node:
                node.remove()
        self._clear_node_cache(False)
        self.__purge_signal_members__()
        del self

    @property
    def _node_count(self) -> int:
        return 1

    def _get_node(self) -> DOMNode:
        if not self._node_cache:
            self._node_cache = self._init_node()
        return self._node_cache

    def _clear_node_cache(self, recursive: bool = True):
        self._node_cache = None

    def _get_existing_node(self) -> DOMNode | None:
        parent_node = self._parent._get_node()
        if parent_node.childNodes.length > self._node_idx:
            existing_node: DOMNode = parent_node.childNodes[self._node_idx]
            return existing_node
        return None

    @abstractmethod
    def _render_html(self, newline: bool = False, indent: int = 2, count: int = 0) -> str: ...
