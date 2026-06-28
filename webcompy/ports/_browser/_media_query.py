from __future__ import annotations

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._media_query import MediaQueryPort
from webcompy.utils._environment import ENVIRONMENT


class BrowserMediaQueryPort(MediaQueryPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserMediaQueryPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser

    def prefers_dark(self) -> bool:
        match_media = self._browser.window.matchMedia
        mql = match_media("(prefers-color-scheme: dark)")
        return bool(mql.matches)
