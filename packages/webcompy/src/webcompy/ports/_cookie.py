"""Cookie port for reading and writing cookies in the current environment."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class CookiePort(ABC):
    """Cookie read/write surface.

    Browser implementations serialize to and parse from
    ``document.cookie``; server implementations may operate on plain stores.
    """

    @abstractmethod
    def get(self, name: str) -> str | None:
        """Read a single cookie value by name.

        Args:
            name: Cookie name.

        Returns:
            Cookie value, or ``None`` if not set.

        """
        ...

    @abstractmethod
    def set(
        self,
        name: str,
        value: str,
        *,
        max_age: int | None = None,
        expires: datetime | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str | None = None,
    ) -> None:
        """Set a cookie.

        Args:
            name: Cookie name.
            value: Cookie value.
            max_age: Lifetime in seconds.
            expires: Absolute expiry timestamp (converted to a UTC date string).
            path: URL path scope (default ``"/"``).
            domain: Domain scope for the cookie.
            secure: Restrict to HTTPS.
            httponly: Prevent JavaScript access via ``document.cookie``.
            samesite: SameSite attribute (``"Strict"``, ``"Lax"``, ``"None"``).

        """
        ...

    @abstractmethod
    def delete(self, name: str, path: str = "/") -> None:
        """Delete a cookie by setting its ``max-age`` to 0.

        Args:
            name: Cookie name.
            path: Path scope of the cookie to delete (must match ``set``).

        """
        ...

    @abstractmethod
    def get_all(self) -> dict[str, str]:
        """Read all cookies as a dict.

        Returns:
            Mapping of cookie names to values.

        """
        ...
