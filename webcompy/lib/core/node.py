from typing import (
    Any,
    Dict,
    List,
    Tuple,
    Union,
    Optional,
    Callable,
    Coroutine
)
from .event import event_handler_wrapper
from .obj_repository import add_obj


EventCallback = Union[Callable[[], Union[None, Coroutine[Any, Any, None]]],
                      Callable[[Any], Union[None, Coroutine[Any, Any, None]]]]
TypeAttributeValue = Union[str, EventCallback, Any, None]
TypeAttributes = Dict[str, TypeAttributeValue]


class VNodeBase:
    __rnode: Optional[Any] = None

    def __init__(
        self,
        tag: str,
        attrs: Optional[TypeAttributes] = None
    ) -> None:
        self.tag: str = tag.lower()
        self.children: List[Union[VNode, VTextNode]] = []
        self.parent: Optional[VNodeBase] = None
        if attrs is not None:
            self.set_attrs(attrs)

    def set_attrs(self, attrs: TypeAttributes):
        self.event_callbacks = self.__extract_event_callback(attrs)
        self.attrs = self.__convert_attributes(attrs)

    @property
    def rnode(self):
        return self.__rnode

    @rnode.setter
    def rnode(self, rnode: Any):
        self.__rnode = rnode

    @staticmethod
    def __extract_event_callback(attrs: TypeAttributes):
        return {
            k[1:]: event_handler_wrapper(v)
            for k, v in attrs.items()
            if k.startswith('@') and callable(v)
        }

    @staticmethod
    def __convert_attributes(attrs: TypeAttributes):
        ret: Dict[str, Optional[str]] = {}
        props = ((k, v) for k, v in attrs.items() if not k.startswith('@'))
        for k, v in props:
            k_lower = k.lower()
            if isinstance(v, str):
                ret[k_lower] = v
            elif v is None:
                ret[k_lower] = None
        return ret


class VTextNode(VNodeBase):
    def __init__(self, text: str) -> None:
        super().__init__('#text', {})
        self.text: str = text


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
        super().__init__(tag, attrs)

    def append_child(self, child: Any):
        self.children.append(self._set_parent(child))

    def _set_parent(self, child: Any):
        if isinstance(child, (VNode, VTextNode)):
            child.parent = self
            return child
        else:
            raise TypeError()

    def update_attr(self, name: str, value: Union[str, Any, None]):
        if self.rnode:
            if isinstance(value, str) or value is None:
                if name.startswith(':'):
                    name = name[1:]
                self.rnode.attrs[name] = value
            else:
                if not name.startswith(':'):
                    name = ':' + name
                self.rnode.attrs[name] = add_obj(value, 'prop:')


def generate_node_mapping(nodes: List[Union[VNode, VTextNode]],
                          parents: Tuple[int, ...],
                          mapping: Dict[Tuple[int, ...], Any]):
    for idx, node in enumerate(nodes):
        current: Tuple[int, ...] = (*parents, idx)
        mapping[current] = node
        generate_node_mapping(node.children, current, mapping)
    return mapping


def generate_vnode_mapping(nodes: List[Union[VNode, VTextNode]]):
    return generate_node_mapping(nodes, tuple(), {})
