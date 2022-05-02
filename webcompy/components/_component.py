from typing import Any, Callable, Type, TypeAlias, TypeGuard, Union
from webcompy.elements.types._element import ElementBase, Element
from webcompy.components._libs import Context, ComponentProperty, generate_id
from webcompy.components._abstract import ComponentAbstract
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.exception import WebComPyException


FuncComponentDef: TypeAlias = Callable[[Context[Any]], ElementChildren]
ClassComponentDef: TypeAlias = Type[ComponentAbstract[Any]]


def _is_function_style_component_def(obj: Any) -> TypeGuard[FuncComponentDef]:
    return callable(obj) and getattr(obj, "__webcompy_componet_definition__", None)


def _is_class_style_component_def(obj: Any) -> TypeGuard[ClassComponentDef]:
    return isinstance(obj, type) and issubclass(obj, ComponentAbstract)


class Component(ElementBase):
    def __init__(
        self,
        component_def: Union[FuncComponentDef, ClassComponentDef],
        props: Any,
        slots: dict[str, Callable[[], ElementChildren]],
    ) -> None:
        self._attrs = {}
        self._event_handlers = {}
        self._ref = None
        self._children = []
        super().__init__()
        self.__init_component(self.__setup(component_def, props, slots))

    def __setup(
        self,
        component_def: Union[FuncComponentDef, ClassComponentDef],
        props: Any,
        slots: dict[str, Callable[[], ElementChildren]],
    ) -> ComponentProperty:
        if _is_class_style_component_def(component_def):
            return component_def.__get_component_instance__(
                Context(props, slots, component_def.__get_name__())
            ).__get_component_property__()
        elif _is_function_style_component_def(component_def):
            component_name = component_def.__name__
            context = Context(props, slots, component_name)
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
        self._property["on_before_destroy"]()
        super()._remove_element(recursive, remove_node)

    def _get_belonging_component(self):
        return self._property["component_id"]

    def _get_belonging_components(self) -> tuple["Component", ...]:
        return (*self._parent._get_belonging_components(), self)
