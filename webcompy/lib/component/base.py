from typing import (
    Any,
    Callable,
    Dict,
    List,
    NewType,
    Optional,
    Union,
    cast,
    final)
from browser import window
from abc import ABCMeta, abstractmethod
from ..core import (
    VNode,
    VTextNode,
    VReactiveTextNode,
    Style,
    Reactive,
    eval_reactive_text,
    eval_reactive_prop,
    generate_rnode_mapping,
    generate_vnode_mapping,
    update_dom,
    register_emitted_arg,
    split_text_nodes,
    parse_html,
    generate_uid_str)


class WebcompyComponentBase(metaclass=ABCMeta):
    tag_name: str

    _scoped_styles: List[Style]
    _use_shadow_dom: bool

    _conponent: Any
    _root: Any
    _refs: Dict[str, Any]

    __template_nodes: List[Any]
    __vdom: List[Union[VNode, VTextNode]]

    @staticmethod
    @abstractmethod
    def get_element_name() -> str:
        ...

    @final
    def render(self):
        if not hasattr(self, '_WebcompyComponentBase__vdom'):
            self.__vdom = self._parse_nodes(self.__template_nodes)
        vdom_mapping = generate_vnode_mapping(self.__vdom)
        rdom_mapping = generate_rnode_mapping(self._root.child_nodes)
        self._refs = update_dom(self._root,
                                vdom_mapping,
                                rdom_mapping)
        self.on_rendered()

    @classmethod
    @final
    def get_scoped_styles(cls) -> List[Style]:
        return cls._scoped_styles

    @property
    @final
    def refs(self) -> Dict[str, Any]:
        return self._refs

    @final
    def emit(self, event_name: str, arg: Optional[Any] = None):
        idx = register_emitted_arg(arg)
        detail = {'detail': {'webcompyEmittedArgument': idx}}
        event = window.CustomEvent.new(event_name, detail)
        self._conponent.dispatchEvent(event)

    def on_connected(self) -> None:
        ...

    def on_rendered(self) -> None:
        ...

    def on_disconnected(self) -> None:
        ...

    @property
    @final
    def _public_attrs(self):
        return {
            name: getattr(self, name)
            for name in dir(self)
            if not (name in set(dir(WebcompyComponentBase)) or name.startswith('_'))
        }

    @final
    def _set_template(self, template: str):
        self.__template_nodes = parse_html(template)
        if hasattr(self, '_WebcompyComponentBase__vdom'):
            self.__vdom = self._parse_nodes(self.__template_nodes)
            if hasattr(self, '_root'):
                self.render()

    @final
    def _eval_statement(
        self,
        stat: str,
        evaluater: Callable[[str, Dict[str, Any], Optional[Dict[str, Any]]], Any],
        setter_action: Callable[[], None]
    ) -> Any:
        reactives: List[Reactive[Any]] = [
            v for v in self._public_attrs.values()
            if isinstance(v, Reactive)
        ]
        for r in reactives:
            def set_setter(reactive: Reactive[Any], _: Any):
                key = generate_uid_str(reactive.setter_actions, 'update:')
                reactive.setter_actions[key] = setter_action
            r.getter_actions['eval_statement:set_setter'] = set_setter
        ret = evaluater(stat, self._public_attrs, {})
        for reactive in reactives:
            del reactive.getter_actions['eval_statement:set_setter']
        return ret

    @final
    def _create_node(self, node: Any) -> VNode:
        node_tag: str = node.nodeName.lower()
        node_attrs = (
            (cast(str, attr.nodeName), cast(Optional[str], attr.nodeValue))
            for attr in map(node.attributes.item, range(node.attributes.length))
        )
        vnode = VNode(node_tag)
        for k, v in node_attrs:
            if v and k.startswith(':'):
                stat = v
                value = self._eval_statement(
                    stat,
                    eval_reactive_prop,
                    lambda: vnode.set_attribute(
                        k[1:],
                        eval_reactive_prop(stat, self._public_attrs)
                    )
                )
                vnode.set_attribute(k, value)
            elif v and k.startswith('@'):
                vnode.bind_event_callback(k, eval(v, self._public_attrs, {}))
            else:
                vnode.set_attribute(k, v)
        return vnode

    @final
    def _parse_nodes(self, nodes: List[Any]):
        return self._parse_nodes_internal(
            nodes,
            VNode('__root__', {})
        ).children

    @final
    def _parse_nodes_internal(self, nodes: List[Any], parent: VNode):
        for el in nodes:
            if el.nodeName == '#text':
                for t, v in split_text_nodes(el.text):
                    if t == 'text':
                        text_node = VTextNode(v)
                    else:
                        reactive_node = VReactiveTextNode()
                        stat = v
                        value = self._eval_statement(
                            stat, eval_reactive_text, lambda: reactive_node.update(
                                eval_reactive_text(
                                    stat, self._public_attrs)))
                        reactive_node.update(value)
                        text_node = reactive_node
                    parent.append_child(text_node)
            else:
                child = self._create_node(el)
                self._parse_nodes_internal(el.childNodes, child)
                parent.append_child(child)
        return parent


WebcompyComponent = NewType('WebcompyComponent', WebcompyComponentBase)
