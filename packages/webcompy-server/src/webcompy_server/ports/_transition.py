from __future__ import annotations

from collections.abc import Callable
from typing import Any

from webcompy.ports._dom import DOMNode
from webcompy.ports._transition import TransitionPort, TransitionStyle


class _EmptyTransitionStyle:
    def get_property_value(self, name: str) -> str:
        return ""


class ServerTransitionPort(TransitionPort):
    @property
    def enabled(self) -> bool:
        return False

    def schedule_next_frame(self, callback: Callable[[], Any]) -> Callable[[], None]:
        return lambda: None

    def schedule_timeout(
        self,
        callback: Callable[[], Any],
        delay_ms: float,
    ) -> Callable[[], None]:
        return lambda: None

    def get_computed_style(self, node: DOMNode) -> TransitionStyle:
        return _EmptyTransitionStyle()
