from typing import Any, cast
from weakref import WeakValueDictionary
from webcompy.reactive._base import ReactiveBase


class ReactiveReceivable:
    __reactive_members__: dict[int, ReactiveBase[Any]]

    def __setattr__(self, name: str, value: Any) -> None:
        if isinstance(value, ReactiveBase):
            self.__set_reactive_member__(cast(ReactiveBase[Any], value))
        super().__setattr__(name, value)

    def __set_reactive_member__(self, value: ReactiveBase[Any]) -> None:
        if not hasattr(self, "__reactive_members__"):
            self.__reactive_members__ = cast(
                dict[int, ReactiveBase[Any]], WeakValueDictionary({})
            )
        self.__reactive_members__[id(value)] = value

    def __purge_reactive_members__(self) -> None:
        if hasattr(self, "__reactive_members__"):
            pass
