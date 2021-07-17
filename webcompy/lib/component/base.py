from typing import (Any, Callable, Dict, List, Optional, Union, cast, final)
from browser import window
from abc import ABCMeta, abstractmethod
from ..core import (
    VNode,
    VTextNode,
    VReactiveTextNode,
    Style,
    Reactive,
    TypeAttributes,
    reactive_text_evaluater,
    reactive_prop_evaluater,
    generate_rnode_mapping,
    generate_vnode_mapping,
    update_dom,
    register_emitted_arg,
    split_text_nodes,
    cleanse_html,
    generate_uid_str)


parseFromString = window.DOMParser.new().parseFromString


class WebcompyComponentBase(metaclass=ABCMeta):
    scoped_styles: List[Style]

    _conponent: Any
    _refs: Dict[str, Any]
    _template: str
    _vdom: Optional[List[Union[VNode, VTextNode]]] = None

    @staticmethod
    @abstractmethod
    def get_element_name() -> str:
        ...

    @final
    def init_vdom(self) -> None:
        self._vdom = self._parse_html(self._template)

    @final
    def render(self):
        if self._vdom is None:
            raise Exception()
        vdom_mapping = generate_vnode_mapping(self._vdom)
        rdom_mapping = generate_rnode_mapping(self._conponent.child_nodes)
        self._refs = update_dom(self._conponent,
                                vdom_mapping,
                                rdom_mapping)
        self.on_rendered()

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
        attrs: TypeAttributes = {}
        for k, v in node_attrs:
            if v and k.startswith('@'):
                attrs[k] = eval(v, self._public_attrs, {})
            elif v and k.startswith(':'):
                stat = v
                attrs[k[1:]] = self._eval_statement(
                    stat,
                    reactive_prop_evaluater,
                    lambda: vnode.update_attr(
                        k[1:],
                        reactive_prop_evaluater(stat, self._public_attrs)
                    )
                )
            else:
                attrs[k] = v
        vnode.set_attrs(attrs)
        return vnode

    @final
    def _parse_nodes(self, nodes: List[Any], parent: VNode):
        for el in nodes:
            if el.nodeName == '#text':
                for t, v in split_text_nodes(el.text):
                    if t == 'text':
                        text_node = VTextNode(v)
                    else:
                        reactive_node = VReactiveTextNode()
                        stat = v
                        value = self._eval_statement(
                            stat, reactive_text_evaluater, lambda: reactive_node.update(
                                reactive_text_evaluater(
                                    stat, self._public_attrs)))
                        reactive_node.update(value)
                        text_node = reactive_node
                    parent.append_child(text_node)
            else:
                child = self._create_node(el)
                self._parse_nodes(el.childNodes, child)
                parent.append_child(child)
        return parent

    @final
    def _parse_html(self, html_text: str) -> List[Union[VNode, VTextNode]]:
        doc = parseFromString(cleanse_html(html_text), 'text/html')
        nodes: List[Any] = doc.getElementsByTagName('body')[0].childNodes
        return self._parse_nodes(nodes, VNode('__root__', {})).children


WebcompyComponent = WebcompyComponentBase
