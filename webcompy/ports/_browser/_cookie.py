from __future__ import annotations

from urllib.parse import unquote

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._cookie import CookiePort
from webcompy.utils._environment import ENVIRONMENT


class BrowserCookiePort(CookiePort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserCookiePort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser

    def get(self, name: str) -> str | None:
        cookies = self.get_all()
        return cookies.get(name)

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
        cookie = f"{name}={value}"
        if max_age is not None:
            cookie += f"; max-age={max_age}"
        if path:
            cookie += f"; path={path}"
        if secure:
            cookie += "; secure"
        if httponly:
            cookie += "; httponly"
        if samesite:
            cookie += f"; samesite={samesite}"
        self._browser.document.cookie = cookie

    def delete(self, name: str, path: str = "/") -> None:
        self.set(name, "", max_age=0, path=path)

    def get_all(self) -> dict[str, str]:
        result: dict[str, str] = {}
        raw = self._browser.document.cookie
        if raw:
            for item in raw.split("; "):
                if "=" in item:
                    key, _, value = item.partition("=")
                    result[unquote(key)] = unquote(value)
        return result
