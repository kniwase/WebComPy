from types import FunctionType
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Type,
    List,
    cast,
    overload)
from .base import WebcompyComponentBase, WebcompyComponent
from .utils import convert_snake_to_kebab, convert_camel_to_kebab
from ..core import Style


FuncStyleComponent = Callable[[], Optional[Dict[str, Any]]]


def define_component(template: str,
                     styles: List[Style] = [],
                     tag_name: Optional[str] = None,
                     use_shadow_dom: bool = False):
    @overload
    def deco(
        definition: FuncStyleComponent
    ) -> Type[WebcompyComponent]:
        ...

    @overload
    def deco(
        definition: Type[WebcompyComponentBase]
    ) -> Type[WebcompyComponent]:
        ...

    def deco(definition: Any) -> Type[WebcompyComponent]:
        def get_tag_name() -> str:
            if tag_name is not None:
                return tag_name
            elif isinstance(definition, FunctionType):
                return convert_snake_to_kebab(definition.__name__)
            elif issubclass(definition, WebcompyComponentBase):
                return convert_camel_to_kebab(definition.__name__)
            else:
                raise TypeError()

        if isinstance(definition, FunctionType):
            ComponentWithVars = function_component_factory(definition)
        elif issubclass(definition, WebcompyComponentBase):
            ComponentWithVars = class_component_factory(definition)
        else:
            raise TypeError()

        class Component(ComponentWithVars):
            _tag_name = get_tag_name()

            _scoped_styles = styles
            _use_shadow_dom = use_shadow_dom

            def __init__(self, conponent: Any, root: Any) -> None:
                super().__init__()
                self._set_template(template)
                self._refs = {}
                self._conponent = conponent
                self._root = root

        return cast(Type[WebcompyComponent], Component)
    return deco


def function_component_factory(setup: FuncStyleComponent):
    def get_vars() -> Dict[str, Any]:
        vars = setup()
        if vars:
            return vars
        else:
            return {}

    class Component(WebcompyComponentBase):
        def __init__(self) -> None:
            super().__init__()
            self._component_vars = get_vars()
    return Component


def class_component_factory(
    cls: Type[WebcompyComponentBase]
):
    class Component(cls):
        def __init__(self) -> None:
            super().__init__()
            self._component_vars = {
                name: getattr(self, name)
                for name in dir(self)
                if not (name in set(dir(WebcompyComponentBase)) or name.startswith('_'))
            }
    return Component
