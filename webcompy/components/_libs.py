import hashlib
import logging
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Literal,
    Protocol,
    TypeAlias,
    TypeVar,
    TypedDict,
    final,
)
from webcompy.exception import WebComPyException
from webcompy.elements.typealias._element_property import ElementChildren


class WebComPyComponentException(WebComPyException):
    pass


NodeGenerator: TypeAlias = Callable[[], ElementChildren]
_Lifecyclehooks: TypeAlias = dict[
    Literal["on_before_rendering", "on_after_rendering", "on_before_destroy"],
    Callable[[], Any],
]

PropsType = TypeVar("PropsType", covariant=True)


@final
class Context(Generic[PropsType]):
    __slots: dict[str, NodeGenerator]
    __props: PropsType

    __on_before_rendering: Callable[[], Any] | None
    __on_after_rendering: Callable[[], Any] | None
    __on_before_destroy: Callable[[], Any] | None

    def __init__(
        self,
        props: PropsType,
        slots: Dict[str, NodeGenerator],
        component_name: str,
    ) -> None:
        self.__props = props
        self.__slots = slots
        self._component_name = component_name
        self.__on_before_rendering = None
        self.__on_after_rendering = None
        self.__on_before_destroy = None

    @property
    def props(self) -> PropsType:
        return self.__props

    def slots(
        self,
        name: str,
        fallback: NodeGenerator | None = None,
    ) -> ElementChildren:
        if name in self.__slots:
            return self.__slots[name]()
        elif fallback is not None:
            return fallback()
        else:
            logging.warning(
                f"Componet '{self._component_name}' is not given a slot named '{name}'"
            )
            return None

    def on_before_rendering(self, func: Callable[[], Any]) -> None:
        self.__on_before_rendering = func

    def on_after_rendering(self, func: Callable[[], Any]) -> None:
        self.__on_after_rendering = func

    def on_before_destroy(self, func: Callable[[], Any]) -> None:
        self.__on_before_destroy = func

    def __get_lifecyclehooks__(self) -> _Lifecyclehooks:
        hooks: _Lifecyclehooks = {}
        if self.__on_before_rendering:
            hooks["on_before_rendering"] = self.__on_before_rendering
        if self.__on_after_rendering:
            hooks["on_after_rendering"] = self.__on_after_rendering
        if self.__on_before_destroy:
            hooks["on_before_destroy"] = self.__on_before_destroy
        return hooks


class ComponentContext(Protocol[PropsType]):
    @property
    def props(self) -> PropsType:
        ...

    def slots(
        self,
        name: str,
        fallback: NodeGenerator | None = None,
    ) -> ElementChildren:
        ...

    def on_before_rendering(self, func: Callable[[], Any]) -> None:
        ...

    def on_after_rendering(self, func: Callable[[], Any]) -> None:
        ...

    def on_before_destroy(self, func: Callable[[], Any]) -> None:
        ...


class ClassStyleComponentContenxt(Protocol[PropsType]):
    @property
    def props(self) -> PropsType:
        ...

    def slots(
        self,
        name: str,
        fallback: NodeGenerator | None = None,
    ) -> ElementChildren:
        ...


@final
class ComponentProperty(TypedDict):
    component_id: str
    component_name: str
    template: ElementChildren
    on_before_rendering: Callable[[], None]
    on_after_rendering: Callable[[], None]
    on_before_destroy: Callable[[], None]


def generate_id(component_name: str) -> str:
    return hashlib.md5(component_name.encode()).hexdigest()
