from __future__ import annotations

from typing import TYPE_CHECKING

from webcompy.app._config import PluginScript
from webcompy.plugin._plugin import WebComPyPlugin, WebComPyPluginException

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp
    from webcompy.app._render_context import RenderContext


class PluginManager:
    def __init__(self, app: WebComPyApp) -> None:
        self._app = app
        self._plugin_classes: list[type[WebComPyPlugin]] = []
        self._plugin_instances: list[WebComPyPlugin] = []

    def discover(self, plugin_paths: list[str]) -> None:
        for path in plugin_paths:
            if ":" not in path:
                raise WebComPyPluginException(
                    f"Invalid plugin path '{path}': missing ':' separator (expected 'module:ClassName')"
                )
            module_path, class_name = path.rsplit(":", 1)
            if not module_path or not class_name:
                raise WebComPyPluginException(f"Invalid plugin path '{path}': module or class name is empty")
            import importlib

            module = importlib.import_module(module_path)
            plugin_cls = getattr(module, class_name)
            if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, WebComPyPlugin):
                raise WebComPyPluginException(f"'{path}' does not point to a WebComPyPlugin subclass")
            self._plugin_classes.append(plugin_cls)

    def init_all(self) -> None:
        for plugin_cls in self._plugin_classes:
            instance = plugin_cls()
            instance.on_app_init(self._app)
            self._plugin_instances.append(instance)

    def init_render_context(self, ctx: RenderContext) -> None:
        for plugin_cls in self._plugin_classes:
            for key, value in plugin_cls.get_providers().items():
                ctx.di_scope.provide(key, value)
        for instance in self._plugin_instances:
            instance.on_render_context_init(ctx)

    def call_on_app_ready(self, ctx: RenderContext) -> None:
        for instance in self._plugin_instances:
            instance.on_app_ready(ctx)

    @property
    def scripts(self) -> list[PluginScript]:
        result: list[PluginScript] = []
        for plugin_cls in self._plugin_classes:
            result.extend(plugin_cls.get_scripts())
        return result
