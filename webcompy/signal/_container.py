from typing import Any, cast
from weakref import WeakValueDictionary

from webcompy.signal._base import SignalBase
from webcompy.signal._graph import consumer_destroy


class SignalReceivable:
    __signal_members__: dict[int, SignalBase[Any]]

    def __setattr__(self, name: str, value: Any) -> None:
        if isinstance(value, SignalBase):
            self.__set_signal_member__(cast("SignalBase[Any]", value))
        super().__setattr__(name, value)

    def __set_signal_member__(self, value: SignalBase[Any]) -> None:
        if not hasattr(self, "__signal_members__"):
            self.__signal_members__ = cast("dict[int, SignalBase[Any]]", WeakValueDictionary({}))
        self.__signal_members__[id(value)] = value

    def __purge_signal_members__(self) -> None:
        if hasattr(self, "__signal_members__"):
            for member in list(self.__signal_members__.values()):
                consumer_destroy(member)
            self.__signal_members__.clear()
