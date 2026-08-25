"""Reactive form aggregation over named ``Field`` instances."""

from __future__ import annotations

from collections.abc import Callable
from inspect import isawaitable
from typing import Any

from webcompy.aio import AsyncWrapper
from webcompy.forms._field import Field
from webcompy.ports._dom import DOMEvent
from webcompy.signal import Computed, Signal


class Form:
    """Reactive aggregation of named ``Field`` instances.

    Derives computed ``valid``/``invalid``/``touched``/``dirty`` state
    from the member fields. ``submit()`` builds an event handler that
    validates the form, runs an async-capable handler with the current
    values, and records submission state in ``submitting`` and
    ``submit_error``.

    Args:
        fields: ``Field`` instances keyed by name.

    Attributes:
        fields: Member ``Field`` instances keyed by name.
        valid: ``Computed[bool]`` — true when every member field is valid.
        invalid: ``Computed[bool]`` — negation of ``valid``.
        touched: ``Computed[bool]`` — true when any member field is
            touched.
        dirty: ``Computed[bool]`` — true when any member field is dirty.
        submitting: ``Signal[bool]`` — true while an async submit handler
            is running.
        submit_error: ``Signal`` holding the exception raised by the last
            failed submission, or ``None``.

    """

    def __init__(self, fields: dict[str, Field[Any]]) -> None:
        self.fields = fields
        self.valid: Computed[bool] = Computed(lambda: all(f.valid.value for f in self.fields.values()))
        self.invalid: Computed[bool] = Computed(lambda: not self.valid.value)
        self.touched: Computed[bool] = Computed(lambda: any(f.touched.value for f in self.fields.values()))
        self.dirty: Computed[bool] = Computed(lambda: any(f.dirty.value for f in self.fields.values()))
        self.submitting: Signal[bool] = Signal(False)
        self.submit_error: Signal[BaseException | None] = Signal(None)

    def touch_all(self) -> None:
        """Mark every member field as touched."""
        for f in self.fields.values():
            f.touched.value = True

    def reset(self) -> None:
        """Reset every member field to its initial state."""
        for f in self.fields.values():
            f.reset()

    def values(self) -> dict[str, Any]:
        """Return a snapshot of the values of all member fields.

        Returns:
            Dict mapping field names to their current values.

        """
        return {name: f.value.value for name, f in self.fields.items()}

    def submit(self, handler: Callable[[dict[str, Any]], Any]) -> Callable[[DOMEvent], None]:
        """Build a submit event handler that validates and runs ``handler``.

        The returned handler calls ``preventDefault()``, touches all
        fields, and stops when the form is invalid. Otherwise it runs
        ``handler`` with the current values, awaiting the result when it
        is awaitable, and stores any raised exception in ``submit_error``.

        Args:
            handler: Callable receiving the field values dict. May be
                synchronous or async.

        Returns:
            A ``DOMEvent`` handler suitable for a form ``submit`` event.

        """

        def on_submit(ev: DOMEvent) -> None:
            ev.preventDefault()
            self.touch_all()
            if not self.valid.value:
                return

            async def run() -> None:
                self.submitting.value = True
                self.submit_error.value = None
                try:
                    result = handler(self.values())
                    if isawaitable(result):
                        await result
                except BaseException as err:
                    self.submit_error.value = err
                finally:
                    self.submitting.value = False

            AsyncWrapper()(run)()

        return on_submit


def use_form(**fields: Field[Any]) -> Form:
    """Create a ``Form`` aggregating the given keyword fields.

    Args:
        **fields: ``Field`` instances keyed by name.

    Returns:
        A ``Form`` over the given fields.

    """
    return Form(fields)
