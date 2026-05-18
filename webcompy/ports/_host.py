from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar, overload

T_co = TypeVar("T_co", covariant=True)


class HostPort(ABC):
    @abstractmethod
    def schedule_macro_task(self, callback: Callable[..., Any]) -> None:
        """Defer a callback to the next macrotask (via ``setTimeout(callback, 0)``).

        In the browser this yields control back to the event loop before
        executing ``callback``. On the server this is a no-op.

        Args:
            callback: Zero-argument callable to execute.
        """
        ...

    @overload
    @abstractmethod
    def create_js_global_getter(self, name: str, *, wrapper: Callable[[Any | None], T_co]) -> Callable[[], T_co]:
        """Create a lazy getter with a wrapper transformation.

        The wrapper is always invoked, receiving ``None`` when the global is
        missing.

        Args:
            name: Name of the JavaScript global to look up.
            wrapper: Transformation applied to the resolved value (or ``None``).

        Returns:
            A zero-argument callable that returns the wrapped value.
        """
        ...

    @overload
    @abstractmethod
    def create_js_global_getter(self, name: str, *, default: T_co) -> Callable[[], Any | T_co]:
        """Create a lazy getter with a fallback value.

        When the global is missing, ``default`` is returned instead of ``None``.

        Args:
            name: Name of the JavaScript global to look up.
            default: Fallback value when the global is missing.

        Returns:
            A zero-argument callable that returns the resolved global or ``default``.
        """
        ...

    @overload
    @abstractmethod
    def create_js_global_getter(
        self,
        name: str,
    ) -> Callable[[], Any | None]:
        """Create a lazy getter with no transformation or fallback.

        Args:
            name: Name of the JavaScript global to look up.

        Returns:
            A zero-argument callable. Returns the resolved global on success,
            ``None`` when the global is missing.
        """
        ...

    @abstractmethod
    def create_js_global_getter(
        self,
        name: str,
        *,
        wrapper: Callable[[Any | None], Any] | None = None,
        default: Any = None,
    ) -> Callable[[], Any]:
        """Create a lazy getter for a JavaScript global.

        Returns a zero-argument function. When called it resolves ``name``
        from the window object (via ``getattr(window, name, None)``).

        Args:
            name: Name of the JavaScript global to look up.
            wrapper: Optional transformation applied to the resolved value.
                     Always invoked — receives ``None`` when the global is
                     missing.
            default: Fallback value used when the global is missing and no
                     ``wrapper`` is provided.

        Returns:
            A zero-argument callable that returns the resolved (and optionally
            wrapped) global, ``default``, or ``None``.
        """
        ...
