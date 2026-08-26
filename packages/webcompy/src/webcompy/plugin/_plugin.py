"""Plugin extension point: ``WebComPyPlugin`` and ``WebComPyPluginException``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from webcompy.app._config import PluginScript

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp
    from webcompy.app._render_context import RenderContext


class WebComPyPluginException(Exception):
    """Error raised for invalid plugin configuration or lifecycle failures."""

    pass


class WebComPyPlugin:
    """Base class for WebComPy plugins providing lifecycle hooks and DI providers.

    Subclass ``WebComPyPlugin`` to expose dependency-injection providers,
    inject client-side scripts, and hook into application and render-context
    lifecycle.

    Attributes:
        name: Human-readable plugin identifier.
        version: Plugin version string.

    """

    name: ClassVar[str] = ""
    version: ClassVar[str] = "0.1.0"

    @staticmethod
    def get_providers() -> dict[object, Any]:
        """Return DI providers contributed by the plugin.

        Returns:
            Mapping of DI keys to provider values contributed for each
            render context.

        """
        return {}

    @staticmethod
    def get_scripts() -> list[PluginScript]:
        """Return scripts injected by the plugin.

        Returns:
            List of ``PluginScript`` descriptors describing script
            elements to add to the rendered page.

        """
        return []

    def on_app_init(self, app: WebComPyApp) -> None:
        """Handle application initialization.

        Args:
            app: Application instance being initialized.

        """
        pass

    @staticmethod
    def get_fetch_middlewares() -> list[Any]:
        """Return fetch middlewares contributed by the plugin.

        Returns:
            List of ``FetchMiddleware`` callables applied in the order
            returned (index ``0`` outermost). An empty list contributes
            nothing.

        """
        return []

    @staticmethod
    def get_rpc_middlewares() -> list[Any]:
        """Return RPC middlewares contributed by the plugin.

        Returns:
            List of ``RpcMiddleware`` callables applied in the order
            returned (index ``0`` outermost). An empty list contributes
            nothing.

        """
        return []

    def on_render_context_init(self, ctx: RenderContext) -> None:
        """Handle creation of a new render context.

        Args:
            ctx: Render context being initialized.

        """
        pass

    def on_app_ready(self, ctx: RenderContext) -> None:
        """Handle the application becoming ready.

        Args:
            ctx: Render context active when the application is ready.

        """
        pass
