from __future__ import annotations
import hashlib
from typing import (
    Any,
    Callable,
    ClassVar,
    Final,
    Generic,
    NoReturn,
    Type,
    TypeVar,
    final,
    overload,
)
from typing_extensions import TypeAlias
from re import compile as re_compile
from webcompy.components._libs import (
    ClassStyleComponentContenxt,
    ComponentProperty,
    WebComPyComponentException,
)
from webcompy.reactive._container import ReactiveReceivable


_camel_to_kebab_pattern: Final = re_compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")
_combinator_pattern: Final = re_compile(r"\s*,\s*|\s*>\s*|\s*\+\s*|\s*~[^=]\s*|\s* \s*")

PropsType = TypeVar("PropsType")


class ComponentAbstract(ReactiveReceivable, Generic[PropsType]):
    __webcompy_component_id__: ClassVar[str]

    __context: ClassStyleComponentContenxt[PropsType]

    name: str

    @final
    @property
    def context(self) -> ClassStyleComponentContenxt[PropsType]:
        return self.__context

    @final
    def __new__(cls) -> NoReturn:
        raise WebComPyComponentException(
            "Component class cannot generate an instance by constructor"
        )

    @final
    def __init_subclass__(cls) -> None:
        cls.__webcompy_component_id__ = hashlib.md5(
            cls.__get_name__().encode()
        ).hexdigest()
        return super().__init_subclass__()

    @final
    @classmethod
    def __get_component_instance__(
        cls, context: ClassStyleComponentContenxt[PropsType]
    ):
        component = super().__new__(cls)
        component.__context = context
        component.__init__()
        return component

    @final
    def __get_component_property__(self) -> ComponentProperty:
        def none():
            return None

        props: dict[str, Callable[[], Any]] = {
            v.__webcompy_component_class_property__: v
            for v in (getattr(self, n) for n in dir(self) if hasattr(self, n))
            if hasattr(v, "__webcompy_component_class_property__")
        }
        return {
            "component_id": self.__webcompy_component_id__,
            "component_name": self.__get_name__(),
            "template": props.get("template", none)(),
            "on_before_rendering": props.get("on_before_rendering", lambda: none),
            "on_after_rendering": props.get("on_after_rendering", lambda: none),
            "on_before_destroy": props.get("on_before_destroy", lambda: none),
        }

    @classmethod
    def __get_name__(cls) -> str:
        return _camel_to_kebab_pattern.sub(
            r"-\1",
            cls.name if hasattr(cls, "name") else cls.__name__,
        ).lower()


ComponentBase: TypeAlias = ComponentAbstract[Any]
NonPropsComponentBase: TypeAlias = ComponentAbstract[None]


@overload
def TypedComponentBase(
    props_type: Type[PropsType],
) -> Type[ComponentAbstract[PropsType]]:
    ...


@overload
def TypedComponentBase(
    props_type: None,
) -> Type[NonPropsComponentBase]:
    ...


def TypedComponentBase(
    props_type: Type[PropsType] | None,
) -> Type[ComponentAbstract[PropsType]] | Type[NonPropsComponentBase]:
    if props_type is None:
        return NonPropsComponentBase
    else:
        return ComponentAbstract[PropsType]


def deco(func: Callable[[], Callable[[], str]]):
    return func


@deco
def func():
    hoge = "hello"
    return lambda: hoge
