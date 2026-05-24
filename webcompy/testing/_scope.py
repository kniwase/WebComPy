from __future__ import annotations

from typing import TYPE_CHECKING, Any

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig

if TYPE_CHECKING:
    from webcompy.components._generator import ComponentGenerator


def create_test_app(
    *,
    root_component: ComponentGenerator,
    **config_overrides: Any,
) -> WebComPyApp:
    valid_fields = set(WebComPyAppConfig.__dataclass_fields__.keys())
    config_kwargs: dict[str, Any] = {k: v for k, v in config_overrides.items() if k in valid_fields}
    config = WebComPyAppConfig(**config_kwargs)
    app = WebComPyApp(root_component=root_component, config=config)
    return app
