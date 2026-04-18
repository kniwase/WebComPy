from typing import NoReturn, TypeVar, final

from webcompy.signal._base import SignalBase
from webcompy.signal._computed import Computed

V = TypeVar("V")


class ReadonlySignal(Computed[V]):
    @final
    def __init__(self) -> NoReturn:
        raise NotImplementedError("ReadonlySignal cannot generate an instance by constructor")

    @classmethod
    def __create_instance__(cls, reactive: SignalBase[V]):
        instance = cls.__new__(cls)
        instance.__set_reactive(reactive)
        return instance

    def __set_reactive(self, reactive: SignalBase[V]):
        super().__init__(lambda: reactive.value)


def readonly(reactive: SignalBase[V]) -> ReadonlySignal[V]:
    return ReadonlySignal.__create_instance__(reactive)
