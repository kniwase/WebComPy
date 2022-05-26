from __future__ import annotations
from typing import Any, Callable, ClassVar, Type
from typing_extensions import TypeAlias, TypeGuard
from uuid import UUID, uuid4
from webcompy.elements.types._element import ElementBase, Element
from webcompy.components._libs import Context, ComponentProperty, generate_id
from webcompy.components._abstract import ComponentAbstract
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.exception import WebComPyException
from webcompy.reactive import ReactiveDict, computed_property


FuncComponentDef: TypeAlias = Callable[[Context[Any]], ElementChildren]
ClassComponentDef: TypeAlias = Type[ComponentAbstract[Any]]


def _is_function_style_component_def(obj: Any) -> TypeGuard[FuncComponentDef]:
    return callable(obj) and getattr(obj, "__webcompy_componet_definition__", None)


def _is_class_style_component_def(obj: Any) -> TypeGuard[ClassComponentDef]:
    return isinstance(obj, type) and issubclass(obj, ComponentAbstract)


class HeadPropsStore:
    def __init__(self) -> None:
        self.titles = ReactiveDict[UUID, str]({})
        self.head_metas = ReactiveDict[UUID, dict[str, dict[str, str]]]({})

    @computed_property
    def title(self):
        return tuple(self.titles.values())[-1]

    @computed_property
    def head_meta(self):
        return {
            key: attributes
            for meta in self.head_metas.values()
            for key, attributes in meta.items()
        }


class Component(ElementBase):
    _head_props: ClassVar = HeadPropsStore()

    def __init__(
        self,
        component_def: FuncComponentDef | ClassComponentDef,
        props: Any,
        slots: dict[str, Callable[[], ElementChildren]],
    ) -> None:
        self._instance_id = uuid4()
        self._attrs = {}
        self._event_handlers = {}
        self._ref = None
        self._children = []
        super().__init__()
        self.__init_component(self.__setup(component_def, props, slots))

    def __setup(
        self,
        component_def: FuncComponentDef | ClassComponentDef,
        props: Any,
        slots: dict[str, Callable[[], ElementChildren]],
    ) -> ComponentProperty:
        if _is_class_style_component_def(component_def):
            return component_def.__get_component_instance__(
                Context(
                    props,
                    slots,
                    component_def.__get_name__(),
                    lambda: Component._head_props.title.value,
                    lambda: Component._head_props.head_meta.value,
                    self._set_title,
                    self._set_meta,
                )
            ).__get_component_property__()
        elif _is_function_style_component_def(component_def):
            component_name = component_def.__name__
            context = Context(
                props,
                slots,
                component_name,
                lambda: Component._head_props.title.value,
                lambda: Component._head_props.head_meta.value,
                self._set_title,
                self._set_meta,
            )
            template = component_def(context)
            hooks = context.__get_lifecyclehooks__()
            return {
                "component_id": generate_id(component_name),
                "component_name": component_name,
                "template": template,
                "on_before_rendering": hooks.get("on_before_rendering", lambda: None),
                "on_after_rendering": hooks.get("on_after_rendering", lambda: None),
                "on_before_destroy": hooks.get("on_before_destroy", lambda: None),
            }
        else:
            raise WebComPyException("Invalid Component Definition")

    def __init_component(self, property: ComponentProperty):
        node = property["template"]
        if not isinstance(node, Element):
            raise WebComPyException(
                "Root Node of Component must be instance of 'Element'"
            )
        self._tag_name = node._tag_name
        self._attrs = {
            **node._attrs,
            "webcompy-component": property["component_name"],
            "webcompy-cid-" + property["component_id"]: True,
        }
        self._event_handlers = node._event_handlers
        self._ref = node._ref
        self._init_children(node._children)
        self._property = property

    def _render(self):
        self._property["on_before_rendering"]()
        super()._render()
        self._property["on_after_rendering"]()

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        if self._instance_id in Component._head_props.titles:
            del Component._head_props.titles[self._instance_id]
        if self._instance_id in Component._head_props.head_metas:
            del Component._head_props.head_metas[self._instance_id]
        self._property["on_before_destroy"]()
        super()._remove_element(recursive, remove_node)

    def _get_belonging_component(self):
        return self._property["component_id"]

    def _get_belonging_components(self) -> tuple["Component", ...]:
        return (*self._parent._get_belonging_components(), self)

    def _set_title(self, title: str):
        Component._head_props.titles[self._instance_id] = title

    def _set_meta(self, key: str, attributes: dict[str, str]):
        meta = Component._head_props.head_metas.get(self._instance_id, {})
        meta[key] = attributes
        Component._head_props.head_metas[self._instance_id] = meta
