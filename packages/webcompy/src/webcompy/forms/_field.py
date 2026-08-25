"""Reactive form field wrapping a ``Signal`` value."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Generic, TypeVar, final

from webcompy.forms._validators import Validator
from webcompy.signal import Computed, Signal

T = TypeVar("T")


@final
class Field(Generic[T]):
    """Reactive form state bound to a single ``Signal`` value.

    Tracks the value, touched/dirty flags, and validation errors as
    signals so form UI reacts to changes. ``errors`` is a ``Computed``
    list produced by running the validators on each read, and ``valid``
    and ``invalid`` are computed booleans derived from it.

    Args:
        signal: Reactive value the field wraps.
        validators: Iterable of ``Validator`` callables run on read.
        name: Optional field name, exposed for form aggregation.

    Attributes:
        name: Field name used for form aggregation, or ``None``.
        value: The wrapped ``Signal[T]`` holding the current value.
        touched: ``Signal[bool]`` — set to true on the field's ``blur``
            event when bound through ``:bind``.
        dirty: ``Signal[bool]`` — set to true when user input is written
            back to ``value`` through ``:bind``.
        errors: ``Computed[list[str]]`` — validation messages produced by
            running the validators on the current value.
        valid: ``Computed[bool]`` — true when ``errors`` is empty.
        invalid: ``Computed[bool]`` — negation of ``valid``.

    """

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
        """Reset the value to the initial value and clear the touched/dirty flags."""
        self.value.value = self._initial
        self.touched.value = False
        self.dirty.value = False


def use_field(
    signal: Signal[T],
    *,
    validators: Iterable[Validator[T]] = (),
    name: str | None = None,
) -> Field[T]:
    """Create a ``Field`` bound to a reactive value.

    Args:
        signal: Reactive value the field wraps.
        validators: Iterable of ``Validator`` callables run on read.
        name: Optional field name, exposed for form aggregation.

    Returns:
        A ``Field`` wrapping ``signal``.

    """
    return Field(signal, validators, name)
