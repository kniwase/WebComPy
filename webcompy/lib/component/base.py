from typing import (
    Any,
    Callable,
    Dict,
    List,
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
    _scoped_styles: List[Style]
    _use_shadow_dom: bool

    _conponent: Any
    _root: Any
    _refs: Dict[str, Any]
    _component_vars: Dict[str, Any]
    _tag_name: str

    __template_nodes: List[Any]
    __vdom: List[Union[VNode, VTextNode]]

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

    @final
    def _render(self):
        if not hasattr(self, '_WebcompyComponentBase__vdom'):
            self.__vdom = self._parse_nodes(self.__template_nodes)
        vdom_mapping = generate_vnode_mapping(self.__vdom)
        rdom_mapping = generate_rnode_mapping(self._root.child_nodes)
        self._refs = update_dom(self._root,
                                vdom_mapping,
                                rdom_mapping)
        self.on_rendered()

    @final
    def _get_component_vars(self):
        return self._component_vars

    @final
    def _set_template(self, template: str):
        self.__template_nodes = parse_html(template)
        if hasattr(self, '_WebcompyComponentBase__vdom'):
            self.__vdom = self._parse_nodes(self.__template_nodes)
            if hasattr(self, '_root'):
                self._render()

    @final
    def _eval_statement(
        self,
        stat: str,
        evaluater: Callable[[str, Dict[str, Any], Optional[Dict[str, Any]]], Any],
        setter_action: Callable[[Any, Any], None]
    ) -> Any:
        reactives: List[Reactive[Any]] = [
            v for v in self._get_component_vars().values()
            if isinstance(v, Reactive)
        ]
        for r in reactives:
            def set_setter(_: Any, reactive: Reactive[Any] = r):
                key = generate_uid_str(
                    reactive.get_setter_actions(), 'update:')
                reactive.add_setter_action(key, setter_action)
            r.add_getter_action('eval_statement:set_setter', set_setter)
        ret = evaluater(stat, self._get_component_vars(), {})
        for reactive in reactives:
            reactive.remove_getter_action('eval_statement:set_setter')
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

                def set_attribute(*_: Any):
                    return vnode.set_attribute(
                        k[1:],
                        eval_reactive_prop(stat, self._get_component_vars())
                    )

                value = self._eval_statement(
                    stat,
                    eval_reactive_prop,
                    set_attribute
                )
                vnode.set_attribute(k, value)
            elif v and k.startswith('@'):
                vnode.bind_event_callback(
                    k, eval(v, self._get_component_vars(), {}))
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

                        def update(*_: Any):
                            return reactive_node.update(
                                eval_reactive_text(
                                    stat, self._get_component_vars())
                            )

                        value = self._eval_statement(
                            stat,
                            eval_reactive_text,
                            update
                        )
                        reactive_node.update(value)
                        text_node = reactive_node
                    parent.append_child(text_node)
            else:
                child = self._create_node(el)
                self._parse_nodes_internal(el.childNodes, child)
                parent.append_child(child)
        return parent


class WebcompyComponent(WebcompyComponentBase):
    @abstractmethod
    def init_component(self, conponent: Any, root: Any) -> None:
        ...

    @property
    @abstractmethod
    def render(self) -> Callable[[], None]:
        ...

    @classmethod
    @abstractmethod
    def get_shadow_dom_mode(cls) -> bool:
        ...

    @classmethod
    @abstractmethod
    def get_scoped_styles(cls) -> List[Style]:
        ...

    @classmethod
    @abstractmethod
    def get_tag_name(cls) -> str:
        ...
