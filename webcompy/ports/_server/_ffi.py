from __future__ import annotations

from typing import Any

from webcompy.ports._ffi import FFIPort


class ServerFFIPort(FFIPort):
    def create_proxy(self, obj: Any) -> Any:
        return obj

    def destroy_proxy(self, proxy: Any) -> None:
        pass

    def is_none(self, obj: Any) -> bool:
        return obj is None

    def to_js(self, obj: Any) -> Any:
        return obj

    def assign(self, target: Any, source: Any) -> None:
        pass
