from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def use_counter(initial: int = 0) -> tuple[Any, Callable[[], None], Callable[[], None]]:
    from webcompy.reactive import Reactive

    count: Reactive[int] = Reactive(initial)

    def increment() -> None:
        count.value += 1

    def decrement() -> None:
        count.value -= 1

    return count, increment, decrement
