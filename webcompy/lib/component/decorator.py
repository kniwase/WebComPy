from types import FunctionType
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Tuple,
    Type,
    List,
    Union,
    cast,
    overload)
from .base import WebcompyComponentBase, WebcompyComponent
from .utils import convert_snake_to_kebab, convert_camel_to_kebab
from .prop import set_prop_callback
from ..core import Style, Reactive
from inspect import Parameter, signature


DefFunc = Callable[
    [],
    Optional[Dict[str, Any]]
]
DefFuncWithProps = Callable[
    [Dict[str, Reactive[Any]]],
    Optional[Dict[str, Any]]
]
FuncStyleComponent = Union[
    DefFunc,
    DefFuncWithProps,
]


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
            ComponentWithVars = function_component_factory(
                definition,
                get_tag_name
            )
        elif issubclass(definition, WebcompyComponentBase):
            ComponentWithVars = class_component_factory(
                definition
            )
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


def get_prop_callback_name(name: str):
    return f'on_change_prop_{name}'


def register_props(
    definition: FuncStyleComponent,
    get_tag_name: Callable[[], str],
):
    params = tuple(signature(definition).parameters.items())
    props_def: Dict[str, Reactive[Any]] = {}
    if len(params) >= 1:
        arg: Any = params[0][1].default
        if isinstance(arg, dict):
            arg = cast(Dict[str, Any], arg)
            for name, reactive in arg.items():
                if isinstance(reactive, Reactive):
                    props_def[name] = reactive
                else:
                    raise TypeError('Prop must be an instance of Reactive.')
        else:
            raise TypeError('Props must be a dict.')

    tag_name = get_tag_name()
    for name in props_def:
        set_prop_callback(name, tag_name, get_prop_callback_name(name))

    return params, props_def


def setup_factory(
    definition: FuncStyleComponent,
    params: Tuple[Tuple[str, Parameter], ...],
    props_def: Dict[str, Reactive[Any]],
):
    def setup(definition: FuncStyleComponent = definition):
        props: Dict[str, Reactive[Any]]
        if len(params) >= 1:
            props = {
                name: prop.clone()
                for name, prop in props_def.items()
            }
            definition = cast(DefFuncWithProps, definition)
            vars = definition(props)
        else:
            definition = cast(DefFunc, definition)
            vars = definition()
            props = {}
        if not vars:
            vars = {}
        return vars, props
    return setup


def function_component_factory(
    definition: FuncStyleComponent,
    get_tag_name: Callable[[], str],
):
    params, props_def = register_props(definition, get_tag_name)
    setup = setup_factory(definition, params, props_def)

    class Component(WebcompyComponentBase):
        def __init__(self) -> None:
            super().__init__()
            vars, props = setup()
            self.__set_props(props)
            self._component_vars = vars

        def __set_props(self, props: Dict[str, Reactive[Any]]):
            for name, reactive in props.items():
                def set_prop(value: Any):
                    reactive.value = value
                self.__setattr__(get_prop_callback_name(name), set_prop)

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
