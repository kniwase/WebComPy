from typing import NoReturn, TypeVar, final
from webcompy.reactive._base import ReactiveBase
from webcompy.reactive._computed import Computed


V = TypeVar("V")


class ReadonlyReactive(Computed[V]):
    @final
    def __init__(self) -> NoReturn:
        raise NotImplementedError(
            "ReadonlyReactive cannot generate an instance by constructor"
        )

    @classmethod
    def __create_instance__(cls, reactive: ReactiveBase[V]):
        instance = cls.__new__(cls)
        instance.__set_reactive(reactive)
        return instance

    def __set_reactive(self, reactive: ReactiveBase[V]):
        super().__init__(lambda: reactive.value)


def readonly(reactive: ReactiveBase[V]) -> ReadonlyReactive[V]:
    return ReadonlyReactive.__create_instance__(reactive)
