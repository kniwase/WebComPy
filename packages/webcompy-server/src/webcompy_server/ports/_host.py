"""Server-side host port."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, overload

from webcompy.ports._host import HostPort

T_co = TypeVar("T_co", covariant=True)


class ServerHostPort(HostPort):
    """Server-side host port with synchronous task execution."""

    def schedule_macro_task(self, callback: Callable[..., Any]) -> None:
        """Schedule ``callback`` as a macro task.

        Args:
            callback: Callback to execute.

        Returns:
            ``None``.

        """
        callback()

    def add_window_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]:
        """Add a window event listener.

        Args:
            event_type: Event type.
            handler: Event handler.

        Returns:
            Callable that removes the listener.

        """
        return lambda: None

    @overload
    def create_js_global_getter(self, name: str, *, wrapper: Callable[[Any | None], T_co]) -> Callable[[], T_co]: ...
    @overload
    def create_js_global_getter(self, name: str, *, default: T_co) -> Callable[[], Any | T_co]: ...
    @overload
    def create_js_global_getter(self, name: str) -> Callable[[], Any | None]: ...
    def create_js_global_getter(
        self,
        name: str,
        *,
        wrapper: Callable[[Any | None], Any] | None = None,
        default: Any = None,
    ) -> Callable[[], Any]:
        """Create a getter for a JavaScript global.

        Args:
            name: Global name.
            wrapper: Optional wrapper for the global value.
            default: Default value when the global is absent.

        Returns:
            Callable that returns the global value or ``default``.

        """

        def _getter() -> Any:
            if wrapper is not None:
                return wrapper(None)
            return default

        return _getter
