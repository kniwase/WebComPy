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

    __title_getter: Callable[[], str]
    __meta_getter: Callable[[], dict[str, dict[str, str]]]
    __title_setter: Callable[[str], None]
    __meta_setter: Callable[[str, dict[str, str]], None]

    def __init__(
        self,
        props: PropsType,
        slots: Dict[str, NodeGenerator],
        component_name: str,
        title_getter: Callable[[], str],
        meta_getter: Callable[[], dict[str, dict[str, str]]],
        title_setter: Callable[[str], None],
        meta_setter: Callable[[str, dict[str, str]], None],
    ) -> None:
        self.__props = props
        self.__slots = slots
        self._component_name = component_name
        self.__on_before_rendering = None
        self.__on_after_rendering = None
        self.__on_before_destroy = None
        self.__title_getter = title_getter
        self.__meta_getter = meta_getter
        self.__title_setter = title_setter
        self.__meta_setter = meta_setter

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

    def get_title(self) -> str:
        return self.__title_getter()

    def get_meta(self) -> dict[str, dict[str, str]]:
        return self.__meta_getter()

    def set_title(self, title: str) -> None:
        self.__title_setter(title)

    def set_meta(self, key: str, attributes: dict[str, str]) -> None:
        self.__meta_setter(key, attributes)

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

    def get_title(self) -> str:
        ...

    def get_meta(self) -> dict[str, dict[str, str]]:
        ...

    def set_title(self, title: str) -> None:
        ...

    def set_meta(self, key: str, attributes: dict[str, str]) -> None:
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

    def get_title(self) -> str:
        ...

    def get_meta(self) -> dict[str, dict[str, str]]:
        ...

    def set_title(self, title: str) -> None:
        ...

    def set_meta(self, key: str, attributes: dict[str, str]) -> None:
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
