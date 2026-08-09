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
    def __init__(self, cookie_header: str = "") -> None:
        self._cookies: dict[str, str] = {}
        self._pending: dict[tuple[str, str], _PendingCookieWrite] = {}
        if cookie_header:
            for item in cookie_header.split("; "):
                if "=" in item:
                    key, _, value = item.partition("=")
                    self._cookies[unquote(key)] = unquote(value)

    def get(self, name: str) -> str | None:
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
        self._cookies.pop(name, None)
        self._pending[(name, path)] = _PendingCookieWrite(name=name, value="", max_age=0, path=path)

    def get_all(self) -> dict[str, str]:
        return dict(self._cookies)

    def get_pending_set_cookie_headers(self) -> list[str]:
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
