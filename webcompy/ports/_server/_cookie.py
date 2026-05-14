from __future__ import annotations

from urllib.parse import unquote

from webcompy.ports._cookie import CookiePort


class ServerCookiePort(CookiePort):
    def __init__(self, cookie_header: str = "") -> None:
        self._cookies: dict[str, str] = {}
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
        path: str = "/",
        secure: bool = False,
        httponly: bool = False,
        samesite: str | None = None,
    ) -> None:
        self._cookies[name] = value

    def delete(self, name: str, path: str = "/") -> None:
        self._cookies.pop(name, None)

    def get_all(self) -> dict[str, str]:
        return dict(self._cookies)
