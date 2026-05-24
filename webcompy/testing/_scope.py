from __future__ import annotations

from typing import TYPE_CHECKING, Any

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.di._scope import DIScope
from webcompy.ports._keys import (
    DOM_PORT_KEY,
    FETCH_PORT_KEY,
    FFI_PORT_KEY,
    HOST_PORT_KEY,
)
from webcompy.ports._server._dom import ServerDOMPort
from webcompy.ports._server._fetch import ServerFetchPort
from webcompy.ports._server._ffi import ServerFFIPort
from webcompy.ports._server._host import ServerHostPort
from webcompy.testing._ports import (
    FakeBrowserDOMPort,
    FakeBrowserFFIPort,
    FakeBrowserHostPort,
)

if TYPE_CHECKING:
    from webcompy.components._generator import ComponentGenerator


def create_browser_scope() -> DIScope:
    scope = DIScope()
    scope.provide(DOM_PORT_KEY, FakeBrowserDOMPort())
    scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
    scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
    return scope


def create_server_scope() -> DIScope:
    scope = DIScope()
    scope.provide(DOM_PORT_KEY, ServerDOMPort())
    scope.provide(HOST_PORT_KEY, ServerHostPort())
    scope.provide(FFI_PORT_KEY, ServerFFIPort())
    scope.provide(FETCH_PORT_KEY, ServerFetchPort())
    return scope


def create_test_app(
    *,
    root_component: ComponentGenerator,
    **config_overrides: Any,
) -> WebComPyApp:
    config_kwargs: dict[str, Any] = {k: v for k, v in config_overrides.items() if hasattr(WebComPyAppConfig, k)}
    config = WebComPyAppConfig(**config_kwargs)
    app = WebComPyApp(root_component=root_component, config=config)
    return app
