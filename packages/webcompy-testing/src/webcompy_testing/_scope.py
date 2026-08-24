"""Test application factory for WebComPy components."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy_server import configure_server_context

if TYPE_CHECKING:
    from webcompy.components._generator import ComponentGenerator


def create_test_app(
    *,
    root_component: ComponentGenerator,
    **config_overrides: Any,
) -> WebComPyApp:
    """Create a ``WebComPyApp`` configured for testing.

    Args:
        root_component: Root component for the test app.
        **config_overrides: Fields forwarded to ``WebComPyAppConfig``.

    Returns:
        A configured ``WebComPyApp`` ready for server-side rendering.

    """
    valid_fields = set(WebComPyAppConfig.__dataclass_fields__.keys())
    config_kwargs: dict[str, Any] = {k: v for k, v in config_overrides.items() if k in valid_fields}
    config = WebComPyAppConfig(**config_kwargs)
    app = WebComPyApp(root_component=root_component, config=config)
    configure_server_context(app)
    return app
