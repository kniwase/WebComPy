"""Server-side FFI port."""

from __future__ import annotations

from typing import Any

from webcompy.ports._ffi import FFIPort


class ServerFFIPort(FFIPort):
    """Server-side no-op FFI port."""

    def create_proxy(self, obj: Any) -> Any:
        """Create a proxy for ``obj``.

        Args:
            obj: Object to wrap.

        Returns:
            ``obj`` unchanged on the server.

        """
        return obj

    def destroy_proxy(self, proxy: Any) -> None:
        """Destroy a previously created proxy.

        Args:
            proxy: Proxy to destroy.

        Returns:
            ``None``.

        """
        pass

    def is_none(self, obj: Any) -> bool:
        """Return whether ``obj`` is ``None``.

        Args:
            obj: Value to check.

        Returns:
            ``True`` if ``obj`` is ``None``.

        """
        return obj is None

    def to_js(self, obj: Any) -> Any:
        """Convert ``obj`` to a JavaScript value.

        Args:
            obj: Value to convert.

        Returns:
            ``obj`` unchanged on the server.

        """
        return obj

    def assign(self, target: Any, source: Any) -> None:
        """Assign properties from ``source`` to ``target``.

        Args:
            target: Target object.
            source: Source object.

        Returns:
            ``None``.

        """
        pass
