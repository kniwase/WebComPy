from __future__ import annotations

import time
from abc import ABC, abstractmethod
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
from webcompy.exception import WebComPyException
from webcompy.router import Router
from webcompy.utils import ENVIRONMENT

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp
    from webcompy.app._root_component import AppDocumentRoot


class RenderContext(ABC):
    _root: AppDocumentRoot
    _di_scope: DIScope
    _component_store: ComponentStore
    _router: Router | None

    def __init__(
        self,
        app: WebComPyApp,
        path: str | None = None,
        *,
        initial_theme: Any = None,
        cookie_header: str | None = None,
    ) -> None:
        self._app = app
        self._config = app._config
        self._profile = app._profile
        self._disposed = False
        self._profile_data: dict[str, float] = {}
        self._defer_depth: int = 0
        self._deferred_callbacks: list = []
        self._initial_theme = initial_theme
        self._cookie_header = cookie_header or ""

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

        self._di_scope.__enter__()
        self._di_scope_token = self._di_scope._token

        self._active_app_token = _active_app_context.set(self)
        self._render_context_cv_token = app._render_context_cv.set(self)

        if ENVIRONMENT == "pyscript":
            _set_app_di_scope(self._di_scope)
            _set_app_instance(self)

        self._register_ports()

        _register_deferred_components()

        app._plugin_manager.init_render_context(self)

        from webcompy.ui.theme._manager import ThemeManager
        from webcompy.ui.theme._theme import THEME_KEY, Theme

        theme_value = self._initial_theme
        if theme_value is None:
            if ENVIRONMENT == "pyscript":
                from webcompy.ui.theme._cookie import read_theme_cookie_value

                theme_value = read_theme_cookie_value()
            if theme_value is None:
                config_theme = self._config.theme
                if config_theme is not None and "default" in config_theme:
                    theme_value = Theme(config_theme["default"])
                else:
                    theme_value = Theme.SYSTEM
        if not isinstance(theme_value, Theme):
            try:
                theme_value = Theme(str(theme_value).lower())
            except ValueError:
                theme_value = Theme.SYSTEM
        manager = ThemeManager(self._app, self, theme_value)
        self._di_scope.provide(THEME_KEY, manager)

        self._record_phase("imports_done")

        from webcompy.app._root_component import AppDocumentRoot

        self._root = AppDocumentRoot(
            app._root_component_def,
            self._router,
            self._di_scope,
            app=self._app,
        )
        manager.register_style()

        app._apply_deferred_ops(self)

        if self._router and path is not None:
            self._root.set_path(path)

        self._record_phase("init_done")

    @abstractmethod
    def _register_ports(self) -> None: ...

    async def render_html(self, **kwargs: Any) -> str:
        raise WebComPyException("render_html() is not available in the browser render context")

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
    def scoped_styles(self):
        self._check_disposed()
        return self._root.scoped_styles

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

    def append_style(self, content: Any) -> None:
        self._check_disposed()
        return self._root.append_style(content)

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

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        _active_app_context.reset(self._active_app_token)
        self._app._render_context_cv.reset(self._render_context_cv_token)
        _set_app_di_scope(None)
        _set_app_instance(None)
        if self._di_scope_token is not None and self._di_scope._token is None:
            _active_di_scope.reset(self._di_scope_token)
        self._di_scope_token = None
        self._di_scope.__exit__(None, None, None)
        self._di_scope.dispose()
        self._root._head_element._cleanup_consumers()
        self._root = None
        self._di_scope = None
        self._component_store = None
        self._router = None

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


class BrowserRenderContext(RenderContext):
    def _register_ports(self) -> None:
        from webcompy.ports._browser._cookie import BrowserCookiePort
        from webcompy.ports._browser._dom import BrowserDOMPort
        from webcompy.ports._browser._fetch import BrowserFetchPort
        from webcompy.ports._browser._ffi import BrowserFFIPort
        from webcompy.ports._browser._history import BrowserHistoryPort
        from webcompy.ports._browser._host import BrowserHostPort
        from webcompy.ports._browser._media_query import BrowserMediaQueryPort
        from webcompy.ports._keys import (
            COOKIE_PORT_KEY,
            DOM_PORT_KEY,
            FETCH_PORT_KEY,
            FFI_PORT_KEY,
            HISTORY_PORT_KEY,
            HOST_PORT_KEY,
            MEDIA_QUERY_PORT_KEY,
        )

        router_mode = self._router.__mode__ if self._router else "history"
        self._di_scope.provide(COOKIE_PORT_KEY, BrowserCookiePort())
        self._di_scope.provide(DOM_PORT_KEY, BrowserDOMPort())
        self._di_scope.provide(FETCH_PORT_KEY, BrowserFetchPort())
        self._di_scope.provide(FFI_PORT_KEY, BrowserFFIPort())
        self._di_scope.provide(HISTORY_PORT_KEY, BrowserHistoryPort(mode=router_mode))
        self._di_scope.provide(HOST_PORT_KEY, BrowserHostPort())
        self._di_scope.provide(MEDIA_QUERY_PORT_KEY, BrowserMediaQueryPort())
