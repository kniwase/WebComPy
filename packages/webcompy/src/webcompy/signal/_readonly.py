from collections.abc import Callable
from typing import TypeVar, final

from webcompy.signal._base import Signal, SignalBase
from webcompy.signal._computed import Computed

V = TypeVar("V")
T = TypeVar("T")


class ReadonlySignal(Computed[V]):
    @final
    def __init__(self) -> None:
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


def use_readonly_signal(initial: T) -> tuple[ReadonlySignal[T], Callable[[T], T]]:
    """Create a read-only reactive value with an external update function.

    ``use_readonly_signal()`` returns a ``(ReadonlySignal[T], Callable[[T], T])``
    pair: the signal is readable reactively but exposes no setter, and the
    returned update function is the sole write path (it sets the value and
    returns the current value, deduplicating equal writes).  It is
    context-free — usable standalone or inside composables — and the value
    is never included in the SSR transfer payload.

    Args:
        initial: The initial value of the signal.

    Returns:
        A tuple of the read-only signal and its update function.
    """
    inner = Signal(initial)
    return readonly(inner), inner.set_value
