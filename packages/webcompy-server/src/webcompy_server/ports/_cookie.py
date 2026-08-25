"""Server-side cookie port."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import format_datetime
from http.cookies import SimpleCookie
from urllib.parse import unquote

from webcompy.ports._cookie import CookiePort


@dataclass
class _PendingCookieWrite:
    name: str
    value: str
    max_age: int | None = None
    expires: datetime | None = None
    path: str = "/"
    domain: str | None = None
    secure: bool = False
    httponly: bool = False
    samesite: str | None = None


class ServerCookiePort(CookiePort):
    """Server-side cookie storage backed by request headers and pending writes.

    Args:
        cookie_header: Raw ``Cookie`` header value from the request.

    """

    def __init__(self, cookie_header: str = "") -> None:
        self._cookies: dict[str, str] = {}
        self._pending: dict[tuple[str, str], _PendingCookieWrite] = {}
        if cookie_header:
            for item in cookie_header.split("; "):
                if "=" in item:
                    key, _, value = item.partition("=")
                    self._cookies[unquote(key)] = unquote(value)

    def get(self, name: str) -> str | None:
        """Return the value of ``name`` if present.

        Args:
            name: Cookie name.

        Returns:
            Cookie value or ``None`` when not set.

        """
        return self._cookies.get(name)

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
        """Set a cookie and record a pending ``Set-Cookie`` header.

        Args:
            name: Cookie name.
            value: Cookie value.
            max_age: Max-Age in seconds.
            expires: Expiration datetime.
            path: Cookie path.
            domain: Cookie domain.
            secure: Whether to set the ``Secure`` flag.
            httponly: Whether to set the ``HttpOnly`` flag.
            samesite: ``SameSite`` attribute value.

        Returns:
            ``None``.

        """
        self._cookies[name] = value
        self._pending[(name, path)] = _PendingCookieWrite(
            name=name,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    def delete(self, name: str, path: str = "/") -> None:
        """Delete a cookie and record a clearing ``Set-Cookie`` header.

        Args:
            name: Cookie name.
            path: Cookie path.

        Returns:
            ``None``.

        """
        self._cookies.pop(name, None)
        self._pending[(name, path)] = _PendingCookieWrite(name=name, value="", max_age=0, path=path)

    def get_all(self) -> dict[str, str]:
        """Return a copy of all cookies.

        Returns:
            Mapping of cookie names to values.

        """
        return dict(self._cookies)

    def get_pending_set_cookie_headers(self) -> list[str]:
        """Build pending ``Set-Cookie`` header strings.

        Returns:
            List of serialized ``Set-Cookie`` header values.

        """
        headers: list[str] = []
        for write in self._pending.values():
            cookie = SimpleCookie()
            cookie[write.name] = write.value
            morsel = cookie[write.name]
            if write.max_age is not None:
                morsel["max-age"] = str(write.max_age)
            if write.expires is not None:
                expires_utc = (
                    write.expires.astimezone(UTC)
                    if write.expires.tzinfo is not None
                    else write.expires.replace(tzinfo=UTC)
                )
                morsel["expires"] = format_datetime(expires_utc, usegmt=True)
            if write.path:
                morsel["path"] = write.path
            if write.domain:
                morsel["domain"] = write.domain
            if write.secure:
                morsel["secure"] = True
            if write.httponly:
                morsel["httponly"] = True
            if write.samesite:
                morsel["samesite"] = write.samesite
            headers.append(morsel.OutputString())
        return headers
