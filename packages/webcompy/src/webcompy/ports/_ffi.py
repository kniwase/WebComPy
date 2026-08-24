"""Foreign-function-interface port bridging Python and JavaScript."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FFIPort(ABC):
    """FFI bridge between Python callables and JavaScript values.

    Implementations wrap the runtime's FFI layer (Pyodide/PyScript FFI in
    the browser) for proxy creation, destruction, null checks, and ordinary
    object conversion.
    """

    @abstractmethod
    def create_proxy(self, obj: Any) -> Any:
        """Wrap a Python callable for use in JavaScript.

        Prevents the wrapped object from being garbage-collected while the
        proxy is alive.

        Args:
            obj: Python callable (or any object) to proxy.

        Returns:
            A JS-side proxy reference.

        """
        ...

    @abstractmethod
    def destroy_proxy(self, proxy: Any) -> None:
        """Release a proxy created by ``create_proxy``.

        Args:
            proxy: The proxy object returned by ``create_proxy``.

        """
        ...

    @abstractmethod
    def is_none(self, obj: Any) -> bool:
        """Check whether a value represents JavaScript ``null`` or ``undefined``.

        Args:
            obj: Value to inspect.

        Returns:
            ``True`` if the value is ``None`` (JS null/undefined).

        """
        ...

    @abstractmethod
    def to_js(self, obj: Any) -> Any:
        """Convert a Python dict to a plain JavaScript object.

        Args:
            obj: Python dictionary to convert.

        Returns:
            JavaScript object equivalent.

        """
        ...

    @abstractmethod
    def assign(self, target: Any, source: Any) -> None:
        """Copy properties from ``source`` to ``target``.

        Equivalent to ``Object.assign(target, source)`` in JavaScript.

        Args:
            target: Destination JavaScript object.
            source: Source JavaScript object whose properties are copied.

        """
        ...
