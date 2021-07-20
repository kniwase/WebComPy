from typing import (
    Any,
    Dict,
    List,
    Tuple,
    Union,
    Optional,
    Callable,
    Coroutine,
    cast
)
from .event import event_handler_wrapper
from .obj_repository import add_obj
from browser import html, document
from abc import abstractmethod


EventCallback = Union[Callable[[], Union[None, Coroutine[Any, Any, None]]],
                      Callable[[Any], Union[None, Coroutine[Any, Any, None]]]]
TypeAttributeValue = Union[str, EventCallback, None]
TypeAttributes = Dict[str, TypeAttributeValue]


class VNodeBase:
    def __init__(self, tag: str) -> None:
        self._tag: str = tag.lower()
        self._parent: Optional[VNode] = None

        self._rnode: Optional[Any] = None

    @property
    def tag(self):
        return self._tag

    @property
    def parent(self):
        return self._parent

    @property
    def rnode(self):
        return self._rnode

    @rnode.setter
    def rnode(self, rnode: Any):
        self._rnode = rnode

    @abstractmethod
    def generate_rnode(self) -> Any:
        ...


class VTextNode(VNodeBase):
    def __init__(self, text: str) -> None:
        super().__init__('#text')
        self.text: str = text

    def generate_rnode(self) -> Any:
        self._rnode = document.createTextNode(self.text)
        return self._rnode


class VReactiveTextNode(VTextNode):
    def __init__(self) -> None:
        super().__init__('')

    def update(self, value: Any):
        self.text = str(value)
        if self.rnode:
            self.rnode.text = self.text


class VNode(VNodeBase):
    def __init__(
        self,
        tag: str,
        attrs: Optional[TypeAttributes] = None
    ) -> None:
        super().__init__(tag)

        self.children: List[Union[VNode, VTextNode]] = []
        self._attrs: dict[str, Optional[str]] = {}
        self._event_callbacks: dict[str, EventCallback] = {}

        if attrs is not None:
            for name, value in attrs:
                if self.__is_event_callback(name, value):
                    func = cast(EventCallback, value)
                    self.bind_event_callback(name, func)
                else:
                    self.set_attribute(name, value)

    @property
    def attrs(self):
        return self._attrs

    @property
    def event_callbacks(self):
        return self._event_callbacks

    def append_child(self, child: Any):
        self.children.append(self._set_parent(child))

    def set_attribute(self, name: str, value: Union[str, Any, None]):
        name = name.lower()
        if isinstance(value, str) or value is None:
            if name.startswith(':'):
                del_target = name
                name = name[1:]
            else:
                del_target = name[1:]
        else:
            if name.startswith(':'):
                del_target = name[1:]
            else:
                del_target = name
                name = ':' + name
            value = add_obj(value, 'prop:')
        # Update VNode Attrs
        self._attrs[name] = value
        if del_target in self._attrs:
            del self._attrs[del_target]
        # Update Real Node Attrs
        if self.rnode:
            self.rnode.attrs[name] = value
            if del_target in self.rnode.attrs:
                del self.rnode.attrs[del_target]

    def bind_event_callback(self, event_name: str, func: EventCallback):
        if callable(func):
            if event_name.startswith('@'):
                event_name = event_name[1:]
            self._event_callbacks[event_name] = event_handler_wrapper(func)
        else:
            raise TypeError()

    def generate_rnode(self) -> Any:
        self._rnode: Any = html.maketag(self.tag)()
        for name, value in self._attrs.items():
            self._rnode.attrs[name] = value
        for event_name, callback in self._event_callbacks.items():
            self._rnode.bind(event_name, callback)
        return self._rnode

    def _set_parent(self, child: Any):
        if isinstance(child, (VNode, VTextNode)):
            child._parent = self
            return child
        else:
            raise TypeError()

    @staticmethod
    def __is_event_callback(name: str, value: TypeAttributeValue):
        return name.startswith('@') and callable(value)


def generate_node_mapping(nodes: List[Union[VNode, VTextNode]],
                          parents: Tuple[int, ...],
                          mapping: Dict[Tuple[int, ...], Any]):
    for idx, node in enumerate(nodes):
        current: Tuple[int, ...] = (*parents, idx)
        mapping[current] = node
        if isinstance(node, VNode):
            generate_node_mapping(node.children, current, mapping)
    return mapping


def generate_vnode_mapping(nodes: List[Union[VNode, VTextNode]]):
    return generate_node_mapping(nodes, tuple(), {})
