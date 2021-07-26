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
from ..core import Style, Reactive, ReactiveData
from inspect import signature


DefFunc = Callable[
    [],
    Optional[Dict[str, Any]]
]
DefFuncWithPropsReactiveData = Callable[
    [ReactiveData],
    Optional[Dict[str, Any]]
]
DefFuncWithPropsReactives = Callable[
    [Dict[str, Reactive[Any]]],
    Optional[Dict[str, Any]]
]
FunctionStyleComponent = Union[
    DefFunc,
    DefFuncWithPropsReactiveData,
    DefFuncWithPropsReactives,
]


def define_component(
    template: str,
    styles: List[Style] = [],
    use_shadow_dom: bool = False,
    tag_name: Optional[str] = None,
):
    @overload
    def deco(
        definition: FunctionStyleComponent
    ) -> Type[WebcompyComponent]:
        ...

    @overload
    def deco(
        definition: Type[WebcompyComponentBase]
    ) -> Type[WebcompyComponent]:
        ...

    def deco(definition: Any) -> Type[WebcompyComponent]:
        name = None
        if tag_name is not None:
            name = tag_name
        if isinstance(definition, FunctionType):
            if name is None:
                name = convert_snake_to_kebab(definition.__name__)
            ComponentWithVars = function_component_factory(
                definition,
                name
            )
        elif issubclass(definition, WebcompyComponentBase):
            if name is None:
                name = convert_camel_to_kebab(definition.__name__)
            ComponentWithVars = class_component_factory(
                definition
            )
        else:
            raise TypeError()

        class Component(ComponentWithVars):
            _tag_name = name

            _scoped_styles = styles
            _use_shadow_dom = use_shadow_dom

            def __init__(self) -> None:
                super().__init__()
                self._set_template(template)
                self._refs = {}

            def __init_component__(
                self,
                conponent: Any,
                root: Any,
                initial_props: Dict[str, Any]
            ) -> None:
                super()._init_vars(initial_props)
                self._conponent = conponent
                self._root = root

            def __render__(self):
                self._render()

            @classmethod
            def get_shadow_dom_mode(cls) -> bool:
                return cls._use_shadow_dom

            @classmethod
            def get_scoped_styles(cls) -> List[Style]:
                return cls._scoped_styles

            @classmethod
            def get_tag_name(cls) -> str:
                return cls._tag_name

        return cast(Type[WebcompyComponent], Component)
    return deco


def get_prop_callback_name(field_name: str):
    return f'on_change_prop_{field_name}'


def parse_args(definition: FunctionStyleComponent):
    params = tuple(signature(definition).parameters.items())
    if len(params) >= 1:
        arg: Any = params[0][1].default
        if isinstance(arg, ReactiveData):
            return arg
        elif isinstance(arg, dict):
            return dict(
                (name, cast(Reactive[Any], reactive))
                for name, reactive in cast(Dict[str, Any], arg).items()
                if isinstance(reactive, Reactive)
            )
        else:
            raise TypeError(
                'Props must be a ReactiveData or Dict of Reactive.')
    else:
        return None


def register_props(
    props_def: Union[ReactiveData, Dict[str, Reactive[Any]], None],
    tag_name: str
):
    if isinstance(props_def, ReactiveData):
        field_names = tuple(props_def.field_names)
    elif isinstance(props_def, dict):
        field_names = tuple(props_def.keys())
    else:
        field_names: Tuple[str, ...] = tuple()
    for name in field_names:
        prop_callback_name = get_prop_callback_name(name)
        set_prop_callback(name, tag_name, prop_callback_name)


def init_props(
    props_def: Union[ReactiveData, Dict[str, Reactive[Any]], None],
    initial_props: Dict[str, Any],
):
    if isinstance(props_def, ReactiveData):
        props = props_def.clone()
        for name, value in initial_props.items():
            if name in props.field_names:
                props.set_field_value(name, value)
    elif isinstance(props_def, dict):
        props = {
            name: prop.clone()
            for name, prop in props_def.items()
        }
        for name, value in initial_props.items():
            if name in props.keys():
                props[name].value = value
    else:
        props = None
    return props


def setup(
    definition: FunctionStyleComponent,
    props: Union[ReactiveData, Dict[str, Reactive[Any]], None]
):
    if isinstance(props, ReactiveData):
        definition = cast(DefFuncWithPropsReactiveData, definition)
        vars = definition(props)
    elif isinstance(props, dict):
        definition = cast(DefFuncWithPropsReactives, definition)
        vars = definition(props)
    else:
        definition = cast(DefFunc, definition)
        vars = definition()
        props = None
    if not vars:
        vars = {}
    return vars


def function_component_factory(
    definition: FunctionStyleComponent,
    tag_name: str
):
    props_def = parse_args(definition)
    register_props(props_def, tag_name)

    class Component(WebcompyComponentBase):
        def __init__(self) -> None:
            super().__init__()

        def _init_vars(self, initial_props: Dict[str, Any]) -> None:
            props = init_props(props_def, initial_props)
            vars = setup(definition, props)

            if isinstance(props, ReactiveData):
                self.__set_props_reactive_data(props)
            elif isinstance(props, dict):
                self.__set_props_dict(props)

            self._component_vars = vars

        def __set_props_reactive_data(self, props: ReactiveData):
            for name in props.field_names:
                def set_prop(
                    value: Any,
                    data: ReactiveData = props,
                    field_name: str = name
                ):
                    data.set_field_value(field_name, value)

                prop_callback_name = get_prop_callback_name(name)
                self.__setattr__(prop_callback_name, set_prop)

        def __set_props_dict(self, props: Dict[str, Reactive[Any]]):
            for name, r in props.items():
                def set_prop(value: Any, reactive: Reactive[Any] = r):
                    reactive.value = value

                prop_callback_name = get_prop_callback_name(name)
                self.__setattr__(prop_callback_name, set_prop)

    return Component


def class_component_factory(cls: Type[WebcompyComponentBase]):
    class Component(cls):
        def __init__(self) -> None:
            super().__init__()

        def _init_vars(self, initial_props: Dict[str, Any]) -> None:
            self._component_vars = {
                name: getattr(self, name)
                for name in dir(self)
                if not (name in dir(WebcompyComponentBase) or name.startswith('_'))
            }

    return Component
