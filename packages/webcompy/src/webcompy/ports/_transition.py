from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Protocol

from webcompy.ports._dom import DOMNode


class TransitionStyle(Protocol):
    """Read-only view over a node's computed style."""

    def get_property_value(self, name: str) -> str: ...


class TransitionPort(ABC):
    """Timing and computed-style surface for CSS class transitions.

    Owns the browser APIs required by ``TransitionElement``: next-frame
    scheduling (double ``requestAnimationFrame``), real-time timeouts with
    cancellation, and computed-style reads. The server port reports
    ``enabled == False`` so transitions degrade to immediate mount/removal.
    """

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Return whether class sequences can run in this environment."""
        ...

    @abstractmethod
    def schedule_next_frame(self, callback: Callable[[], Any]) -> Callable[[], None]:
        """Run ``callback`` after the next animation frame.

        In the browser the callback is scheduled through a double
        ``requestAnimationFrame`` so the pre-swap state is painted first; in
        non-browser environments the returned cancel function is a no-op and
        the callback never runs.

        Args:
            callback: Zero-argument callable to execute.

        Returns:
            A cancel function; calling it prevents ``callback`` from running.

        """
        ...

    @abstractmethod
    def schedule_timeout(
        self,
        callback: Callable[[], Any],
        delay_ms: float,
    ) -> Callable[[], None]:
        """Run ``callback`` after ``delay_ms`` milliseconds.

        Args:
            callback: Zero-argument callable to execute.
            delay_ms: Delay in milliseconds.

        Returns:
            A cancel function; calling it prevents ``callback`` from running.

        """
        ...

    @abstractmethod
    def get_computed_style(self, node: DOMNode) -> TransitionStyle:
        """Return a read-only view of ``node``'s computed style.

        Args:
            node: The DOM node whose computed style is requested.

        Returns:
            A style view exposing ``get_property_value(name)``.

        """
        ...
