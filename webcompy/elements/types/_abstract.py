from __future__ import annotations
from abc import abstractmethod
from typing import cast
from webcompy.elements._dom_objs import DOMNode
from webcompy.reactive._base import ReactiveStore
from webcompy.reactive._container import ReactiveReceivable
from webcompy._browser._modules import browser
from webcompy.exception import WebComPyException


class ElementAbstract(ReactiveReceivable):
    _node_idx: int
    _node_cache: DOMNode | None = None
    _mounted: bool | None = None
    _remount_to: DOMNode | None = None
    _callback_ids: set[int]
    __parent: ElementAbstract

    def __init__(self) -> None:
        self._node_cache = None
        self._mounted = None
        self._remount_to = None
        self._callback_ids: set[int] = set()

    @property
    def _parent(self) -> "ElementAbstract":
        return self.__parent

    @_parent.setter
    def _parent(self, parent: "ElementAbstract"):
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
            self._remount_to = cast(DOMNode, browser.document.createTextNode(""))
            parent_node.replaceChild(self._remount_to, self._node_cache)
            self._mounted = False
        else:
            raise WebComPyException("Not in Browser environment.")

    @abstractmethod
    def _init_node(self) -> DOMNode:
        ...

    def _set_callback_id(self, callback_id: int):
        self._callback_ids.add(callback_id)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        for callback_id in self._callback_ids:
            ReactiveStore.remove_callback(callback_id)
        if remove_node:
            node = self._get_node()
            if node:
                node.remove()
        self._clear_node_cache(False)
        self.__purge_reactive_members__()
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

    def _get_prerendered_node(self) -> DOMNode | None:
        parent_node = self._parent._get_node()
        if parent_node.childNodes.length > self._node_idx:
            prerendered_node: DOMNode = parent_node.childNodes[self._node_idx]
            return prerendered_node
        return None

    @abstractmethod
    def _render_html(
        self, newline: bool = False, indent: int = 2, count: int = 0
    ) -> str:
        ...
