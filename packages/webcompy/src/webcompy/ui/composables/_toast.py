"""Toast queue composable returning a push function and queue state."""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from webcompy.components._hooks import _register_before_destroy_chained
from webcompy.di import inject
from webcompy.ports._keys import TRANSITION_PORT_KEY
from webcompy.signal import Signal, use_state


@dataclass(frozen=True)
class ToastRecord:
    """Single toast entry."""

    id: str
    message: str
    variant: Literal["info", "success", "warning", "error"]
    duration: float | None
    leaving: bool = False


class ToastState:
    """Queue state and dismissal handle for a Toast host."""

    def __init__(self, toasts: Signal[list[ToastRecord]], dismiss: Callable[[str], None]) -> None:
        self.toasts = toasts
        self.dismiss = dismiss


ToastPush = Callable[[str, Literal["info", "success", "warning", "error"], float | None], str]


def use_toast() -> tuple[ToastPush, ToastState]:
    """Create a component-scoped toast queue.

    Returns:
        A tuple of a push function and the queue state. The push
        function accepts a message, variant, and duration in seconds
        (``None`` disables auto-dismiss).

    """
    toasts: Signal[list[ToastRecord]] = use_state(lambda: [])  # type: ignore[arg-type]
    timers: dict[str, Callable[[], None]] = {}

    def _remove(record_id: str) -> None:
        current = list(toasts.value)
        toasts.value = [t for t in current if t.id != record_id]
        cancel = timers.pop(record_id, None)
        if cancel is not None:
            with contextlib.suppress(Exception):
                cancel()

    def _dismiss(record_id: str) -> None:
        # Cancel auto-dismiss timer
        cancel = timers.pop(record_id, None)
        if cancel is not None:
            with contextlib.suppress(Exception):
                cancel()
        # Mark leaving, Transition will handle leave then call _remove via on_leave_end
        current = list(toasts.value)
        found = False
        for idx, rec in enumerate(current):
            if rec.id == record_id and not rec.leaving:
                current[idx] = ToastRecord(
                    id=rec.id, message=rec.message, variant=rec.variant, duration=rec.duration, leaving=True
                )
                found = True
                break
        if found:
            toasts.value = current
        else:
            # Already leaving or not found — remove directly
            _remove(record_id)

    def _push(
        message: str,
        variant: Literal["info", "success", "warning", "error"] = "info",
        duration: float | None = 3.0,
    ) -> str:
        rec_id = uuid.uuid4().hex[:8]
        record = ToastRecord(id=rec_id, message=message, variant=variant, duration=duration, leaving=False)
        toasts.value = [*list(toasts.value), record]
        if duration is not None:
            try:
                port = inject(TRANSITION_PORT_KEY, default=None)
                if port is not None:
                    ms = int(duration * 1000)

                    def _auto() -> None:
                        _dismiss(rec_id)

                    cancel = port.schedule_timeout(_auto, float(ms))
                    timers[rec_id] = cancel
            except Exception:
                pass
        return rec_id

    def _cleanup() -> None:
        for cancel in list(timers.values()):
            with contextlib.suppress(Exception):
                cancel()
        timers.clear()

    _register_before_destroy_chained(_cleanup)

    state = ToastState(toasts=toasts, dismiss=_dismiss)
    # Attach _remove for host's on_leave_end
    state._remove = _remove  # type: ignore[attr-defined]

    return _push, state
