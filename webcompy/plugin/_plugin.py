from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from webcompy.app._config import PluginScript

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp


class WebComPyPluginException(Exception):
    pass


class WebComPyPlugin:
    name: ClassVar[str] = ""
    version: ClassVar[str] = "0.1.0"

    @staticmethod
    def get_providers() -> dict[object, Any]:
        return {}

    @staticmethod
    def get_scripts() -> list[PluginScript]:
        return []

    def on_app_init(self, app: WebComPyApp) -> None:
        pass

    def on_app_ready(self, app: WebComPyApp) -> None:
        pass
