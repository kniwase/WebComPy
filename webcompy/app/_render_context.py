from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from webcompy.app._config import WebComPyAppConfig
from webcompy.components._component import (
    _active_app_context,
    _set_app_instance,
)
from webcompy.components._generator import (
    ComponentStore,
    _register_deferred_components,
)
from webcompy.di._keys import _COMPONENT_STORE_KEY
from webcompy.di._scope import DIScope, _active_di_scope, _set_app_di_scope
from webcompy.router import Router
from webcompy.utils import ENVIRONMENT

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp
    from webcompy.app._root_component import AppDocumentRoot


class RenderContext:
    _root: AppDocumentRoot
    _di_scope: DIScope
    _component_store: ComponentStore
    _router: Router | None

    def __init__(self, app: WebComPyApp, path: str | None = None) -> None:
        self._app = app
        self._config = app._config
        self._profile = app._profile
        self._disposed = False
        self._profile_data: dict[str, float] = {}
        self._defer_depth: int = 0
        self._deferred_callbacks: list = []

        self._record_phase("init_start")

        self._di_scope = DIScope()
        self._component_store = ComponentStore()
        self._di_scope.provide(_COMPONENT_STORE_KEY, self._component_store)

        self._router = None
        if app._router:
            pages = [route[4] for route in app._router.__routes__]
            self._router = Router(
                *pages,
                default=app._router._default,
                mode=app._router.__mode__,
                base_url=app._router.__base_url__ or "",
            )
        router_mode = (
            self._router.__mode__ if self._router else "history"  # type: ignore[assignment]
        )

        self._di_scope.__enter__()
        self._di_scope_token = self._di_scope._token

        if ENVIRONMENT == "pyscript":
            _set_app_di_scope(self._di_scope)
            _set_app_instance(self)
            from webcompy.ports._browser._cookie import BrowserCookiePort
            from webcompy.ports._browser._dom import BrowserDOMPort
            from webcompy.ports._browser._fetch import BrowserFetchPort
            from webcompy.ports._browser._ffi import BrowserFFIPort
            from webcompy.ports._browser._history import BrowserHistoryPort
            from webcompy.ports._browser._host import BrowserHostPort
            from webcompy.ports._keys import (
                COOKIE_PORT_KEY,
                DOM_PORT_KEY,
                FETCH_PORT_KEY,
                FFI_PORT_KEY,
                HISTORY_PORT_KEY,
                HOST_PORT_KEY,
            )

            self._di_scope.provide(COOKIE_PORT_KEY, BrowserCookiePort())
            self._di_scope.provide(DOM_PORT_KEY, BrowserDOMPort())
            self._di_scope.provide(FETCH_PORT_KEY, BrowserFetchPort())
            self._di_scope.provide(FFI_PORT_KEY, BrowserFFIPort())
            self._di_scope.provide(HISTORY_PORT_KEY, BrowserHistoryPort(mode=router_mode))
            self._di_scope.provide(HOST_PORT_KEY, BrowserHostPort())
        else:
            from webcompy.ports._keys import (
                COOKIE_PORT_KEY,
                DOM_PORT_KEY,
                FETCH_PORT_KEY,
                FFI_PORT_KEY,
                HISTORY_PORT_KEY,
                HOST_PORT_KEY,
            )
            from webcompy.ports._server._cookie import ServerCookiePort
            from webcompy.ports._server._dom import ServerDOMPort
            from webcompy.ports._server._fetch import ServerFetchPort
            from webcompy.ports._server._ffi import ServerFFIPort
            from webcompy.ports._server._history import ServerHistoryPort
            from webcompy.ports._server._host import ServerHostPort

            self._di_scope.provide(COOKIE_PORT_KEY, ServerCookiePort())
            self._di_scope.provide(DOM_PORT_KEY, ServerDOMPort())
            self._di_scope.provide(FETCH_PORT_KEY, ServerFetchPort())
            self._di_scope.provide(FFI_PORT_KEY, ServerFFIPort())
            self._di_scope.provide(HISTORY_PORT_KEY, ServerHistoryPort(mode=router_mode))
            self._di_scope.provide(HOST_PORT_KEY, ServerHostPort())

        _register_deferred_components()

        app._plugin_manager.init_render_context(self)

        self._record_phase("imports_done")

        from webcompy.app._root_component import AppDocumentRoot

        self._root = AppDocumentRoot(
            app._root_component_def,
            self._router,
            self._di_scope,
            app=self._app,
        )

        app._apply_deferred_ops(self)

        if self._router and path is not None:
            self._root.set_path(path)

        self._record_phase("init_done")

    def _check_disposed(self) -> None:
        if self._disposed:
            raise RuntimeError("RenderContext has been disposed")

    @property
    def config(self) -> WebComPyAppConfig:
        return self._config

    @property
    def profile_data(self) -> dict[str, float] | None:
        return self._profile_data if self._profile else None

    def _record_phase(self, name: str) -> None:
        if self._profile:
            self._profile_data[name] = time.perf_counter()

    @property
    def di_scope(self) -> DIScope:
        self._check_disposed()
        return self._di_scope

    def provide(self, key: object, value: Any) -> None:
        self._check_disposed()
        self._di_scope.provide(key, value)

    def render_html(self, **kwargs: Any) -> str:
        from webcompy.cli._html import generate_html

        return generate_html(self, **kwargs)

    def dispose(self) -> None:
        self._disposed = True
        _active_app_context.set(None)
        if ENVIRONMENT == "pyscript":
            _set_app_di_scope(None)
            _set_app_instance(None)
        if self._app._render_context is self:
            self._app._render_context = None
        if self._di_scope_token is not None and self._di_scope._token is None:
            _active_di_scope.reset(self._di_scope_token)
        self._di_scope_token = None
        self._di_scope.__exit__(None, None, None)
        self._di_scope.dispose()
        self._root = None  # type: ignore[assignment]
        self._di_scope = None  # type: ignore[assignment]
        self._component_store = None  # type: ignore[assignment]
        self._router = None

    @property
    def routes(self):
        self._check_disposed()
        return self._root.routes

    @property
    def router_mode(self):
        self._check_disposed()
        return self._root.router_mode

    def set_path(self, path: str):
        self._check_disposed()
        return self._root.set_path(path)

    @property
    def head(self):
        self._check_disposed()
        return self._root.head

    @property
    def style(self):
        self._check_disposed()
        return self._root.style

    @property
    def scripts(self):
        self._check_disposed()
        return self._root.scripts

    def set_title(self, title: str) -> None:
        self._check_disposed()
        return self._root.set_title(title)

    def set_meta(self, key: str, attributes: dict[str, str]) -> None:
        self._check_disposed()
        return self._root.set_meta(key, attributes)

    def append_link(self, attributes: dict[str, str]) -> None:
        self._check_disposed()
        return self._root.append_link(attributes)

    def append_script(
        self,
        attributes: dict[str, str],
        script: str | None = None,
        in_head: bool = False,
    ) -> None:
        self._check_disposed()
        return self._root.append_script(attributes, script, in_head)

    def set_head(self, head: Any) -> None:
        self._check_disposed()
        return self._root.set_head(head)

    def update_head(self, head: Any) -> None:
        self._check_disposed()
        return self._root.update_head(head)

    def set_html_attr(self, key: str, value: Any) -> None:
        self._check_disposed()
        return self._root.set_html_attr(key, value)

    def remove_html_attr(self, key: str) -> None:
        self._check_disposed()
        return self._root.remove_html_attr(key)

    @property
    def html_attrs(self):
        self._check_disposed()
        return self._root.html_attrs
