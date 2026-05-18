from __future__ import annotations

from typing import Any

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._ffi import FFIPort
from webcompy.utils._environment import ENVIRONMENT


class BrowserFFIPort(FFIPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserFFIPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser

    def create_proxy(self, obj: Any) -> Any:
        return self._browser.pyscript.ffi.create_proxy(obj)

    def destroy_proxy(self, proxy: Any) -> None:
        if hasattr(proxy, "destroy"):
            proxy.destroy()

    def is_none(self, obj: Any) -> bool:
        return obj is None

    def to_js(self, obj: Any) -> Any:
        return self._browser.pyscript.ffi.to_js(obj)

    def assign(self, target: Any, source: Any) -> None:
        self._browser.pyscript.ffi.assign(target, source)
