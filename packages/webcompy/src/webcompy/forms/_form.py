from __future__ import annotations

from collections.abc import Callable
from inspect import isawaitable
from typing import Any

from webcompy.aio import AsyncWrapper
from webcompy.forms._field import Field
from webcompy.ports._dom import DOMEvent
from webcompy.signal import Computed, Signal


class Form:
    def __init__(self, fields: dict[str, Field[Any]]) -> None:
        self.fields = fields
        self.valid: Computed[bool] = Computed(lambda: all(f.valid.value for f in self.fields.values()))
        self.invalid: Computed[bool] = Computed(lambda: not self.valid.value)
        self.touched: Computed[bool] = Computed(lambda: any(f.touched.value for f in self.fields.values()))
        self.dirty: Computed[bool] = Computed(lambda: any(f.dirty.value for f in self.fields.values()))
        self.submitting: Signal[bool] = Signal(False)
        self.submit_error: Signal[BaseException | None] = Signal(None)

    def touch_all(self) -> None:
        for f in self.fields.values():
            f.touched.value = True

    def reset(self) -> None:
        for f in self.fields.values():
            f.reset()

    def values(self) -> dict[str, Any]:
        return {name: f.value.value for name, f in self.fields.items()}

    def submit(self, handler: Callable[[dict[str, Any]], Any]) -> Callable[[DOMEvent], None]:
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
    return Form(fields)
