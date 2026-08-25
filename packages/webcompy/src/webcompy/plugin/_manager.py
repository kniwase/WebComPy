"""Plugin discovery and lifecycle management: ``PluginManager``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from webcompy.app._config import PluginScript
from webcompy.plugin._plugin import WebComPyPlugin, WebComPyPluginException

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp
    from webcompy.app._render_context import RenderContext


class PluginManager:
    """Discover plugin classes and drive their lifecycle hooks for one app.

    Plugin paths are resolved with ``discover``, instantiated with
    ``init_all``, and then called back per render context
    (``init_render_context``) and once the app is ready
    (``call_on_app_ready``).

    Args:
        app: Application instance the plugins extend.

    Attributes:
        scripts: Aggregated scripts contributed by all discovered
            plugins.

    """

    def __init__(self, app: WebComPyApp) -> None:
        self._app = app
        self._plugin_classes: list[type[WebComPyPlugin]] = []
        self._plugin_instances: list[WebComPyPlugin] = []

    def discover(self, plugin_paths: list[str]) -> None:
        """Resolve ``"module:ClassName"`` paths to plugin subclasses.

        Imported classes are validated as ``WebComPyPlugin`` subclasses
        and recorded for later initialization.

        Args:
            plugin_paths: Plugin references formatted as
                ``"module:ClassName"``.

        Raises:
            WebComPyPluginException: If a path is malformed or does not
                point to a ``WebComPyPlugin`` subclass.

        """
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
        """Instantiate all discovered plugins and call their ``on_app_init`` hooks."""
        for plugin_cls in self._plugin_classes:
            instance = plugin_cls()
            instance.on_app_init(self._app)
            self._plugin_instances.append(instance)

    def init_render_context(self, ctx: RenderContext) -> None:
        """Provide plugin DI values and initialize plugins for a render context.

        Args:
            ctx: Render context receiving the plugin providers and
                lifecycle callbacks.

        """
        for plugin_cls in self._plugin_classes:
            for key, value in plugin_cls.get_providers().items():
                ctx.di_scope.provide(key, value)
        for instance in self._plugin_instances:
            instance.on_render_context_init(ctx)
        from webcompy.di._keys import RPC_MIDDLEWARE_KEY
        from webcompy.ports._keys import FETCH_MIDDLEWARE_KEY

        for plugin_cls in self._plugin_classes:
            fetch_middlewares = plugin_cls.get_fetch_middlewares()
            if fetch_middlewares:
                fetch_registry = ctx.di_scope.inject(
                    FETCH_MIDDLEWARE_KEY,  # type: ignore[type-var]
                    default=None,
                )
                if fetch_registry is not None:
                    for middleware in fetch_middlewares:
                        fetch_registry.use(middleware)  # type: ignore[attr-defined]
        for plugin_cls in self._plugin_classes:
            rpc_middlewares = plugin_cls.get_rpc_middlewares()
            if rpc_middlewares:
                rpc_registry = ctx.di_scope.inject(
                    RPC_MIDDLEWARE_KEY,  # type: ignore[type-var]
                    default=None,
                )
                if rpc_registry is not None:
                    for middleware in rpc_middlewares:
                        rpc_registry.use(middleware)  # type: ignore[attr-defined]

    def call_on_app_ready(self, ctx: RenderContext) -> None:
        """Notify all plugins that the application is ready.

        Args:
            ctx: Render context active when the application becomes ready.

        """
        for instance in self._plugin_instances:
            instance.on_app_ready(ctx)

    @property
    def scripts(self) -> list[PluginScript]:
        """Aggregate scripts contributed by all discovered plugins."""
        result: list[PluginScript] = []
        for plugin_cls in self._plugin_classes:
            result.extend(plugin_cls.get_scripts())
        return result
