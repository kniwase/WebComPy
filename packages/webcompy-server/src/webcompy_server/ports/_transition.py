"""Server-side transition port."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from webcompy.ports._dom import DOMNode
from webcompy.ports._transition import TransitionPort, TransitionStyle


class _EmptyTransitionStyle:
    def get_property_value(self, name: str) -> str:
        return ""


class ServerTransitionPort(TransitionPort):
    """Server-side no-op transition port.

    Attributes:
        enabled: Always ``False`` on the server, so transitions degrade to
            immediate mount/removal.

    """

    @property
    def enabled(self) -> bool:
        """Return whether transitions are enabled.

        Returns:
            ``False`` on the server.

        """
        return False

    def schedule_next_frame(self, callback: Callable[[], Any]) -> Callable[[], None]:
        """Schedule ``callback`` for the next frame.

        Args:
            callback: Callback to schedule.

        Returns:
            Callable that cancels the schedule.

        """
        return lambda: None

    def schedule_timeout(
        self,
        callback: Callable[[], Any],
        delay_ms: float,
    ) -> Callable[[], None]:
        """Schedule ``callback`` after a delay.

        Args:
            callback: Callback to schedule.
            delay_ms: Delay in milliseconds.

        Returns:
            Callable that cancels the schedule.

        """
        return lambda: None

    def get_computed_style(self, node: DOMNode) -> TransitionStyle:
        """Return computed style for ``node``.

        Args:
            node: DOM node.

        Returns:
            Empty transition style on the server.

        """
        return _EmptyTransitionStyle()
