from __future__ import annotations

from collections.abc import Iterable
from typing import Generic, TypeVar

from webcompy.forms._validators import Validator
from webcompy.signal import Computed, Signal

T = TypeVar("T")


class Field(Generic[T]):
    def __init__(
        self,
        signal: Signal[T],
        validators: Iterable[Validator[T]] = (),
        name: str | None = None,
    ) -> None:
        self.name = name
        self.value: Signal[T] = signal
        self.touched: Signal[bool] = Signal(False)
        self.dirty: Signal[bool] = Signal(False)
        self._validators = list(validators)
        self._initial = signal.value
        self.errors: Computed[list[str]] = Computed(self._validate)
        self.valid: Computed[bool] = Computed(lambda: len(self.errors.value) == 0)
        self.invalid: Computed[bool] = Computed(lambda: not self.valid.value)

    def _validate(self) -> list[str]:
        return [msg for validator in self._validators if (msg := validator(self.value.value)) is not None]

    def reset(self) -> None:
        self.value.value = self._initial
        self.touched.value = False
        self.dirty.value = False


def use_field(
    signal: Signal[T],
    *,
    validators: Iterable[Validator[T]] = (),
    name: str | None = None,
) -> Field[T]:
    return Field(signal, validators, name)
