from __future__ import annotations

import logging
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
from webcompy.di._keys import (
    _APP_KEY,
    _COMPONENT_STORE_KEY,
    _TELEPORT_REGISTRY_KEY,
    RPC_REGISTRY_KEY,
)
from webcompy.di._scope import DIScope, _active_di_scope, _set_app_di_scope
from webcompy.elements.types._teleport import _TeleportTargetRegistry
from webcompy.exception import WebComPyException
from webcompy.router import Router
from webcompy.utils import ENVIRONMENT

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp
    from webcompy.app._root_component import AppDocumentRoot


class RenderContext(ABC):
    _root: AppDocumentRoot | None
    _di_scope: DIScope | None
    _component_store: ComponentStore | None
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
        self._di_scope.provide(_APP_KEY, app)
        self._di_scope.provide(_COMPONENT_STORE_KEY, self._component_store)
        self._di_scope.provide(RPC_REGISTRY_KEY, app._rpc_registry)
        self._di_scope.provide(_TELEPORT_REGISTRY_KEY, _TeleportTargetRegistry())

        self._router = None
        if app._router:
            self._router = app._router._clone_for_request()

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
        assert self._root is not None
        return self._root.routes

    @property
    def router_mode(self):
        self._check_disposed()
        assert self._root is not None
        return self._root.router_mode

    def set_path(self, path: str):
        self._check_disposed()
        assert self._root is not None
        return self._root.set_path(path)

    @property
    def head(self):
        self._check_disposed()
        assert self._root is not None
        return self._root.head

    @property
    def scoped_styles(self):
        self._check_disposed()
        assert self._root is not None
        return self._root.scoped_styles

    @property
    def scripts(self):
        self._check_disposed()
        assert self._root is not None
        return self._root.scripts

    def set_title(self, title: str) -> None:
        self._check_disposed()
        assert self._root is not None
        return self._root.set_title(title)

    def set_meta(self, key: str, attributes: dict[str, str]) -> None:
        self._check_disposed()
        assert self._root is not None
        return self._root.set_meta(key, attributes)

    def append_link(self, attributes: dict[str, str]) -> None:
        self._check_disposed()
        assert self._root is not None
        return self._root.append_link(attributes)

    def append_script(
        self,
        attributes: dict[str, str],
        script: str | None = None,
        in_head: bool = False,
    ) -> None:
        self._check_disposed()
        assert self._root is not None
        return self._root.append_script(attributes, script, in_head)

    def append_style(self, content: Any) -> None:
        self._check_disposed()
        assert self._root is not None
        return self._root.append_style(content)

    def set_head(self, head: Any) -> None:
        self._check_disposed()
        assert self._root is not None
        return self._root.set_head(head)

    def update_head(self, head: Any) -> None:
        self._check_disposed()
        assert self._root is not None
        return self._root.update_head(head)

    def set_html_attr(self, key: str, value: Any) -> None:
        self._check_disposed()
        assert self._root is not None
        return self._root.set_html_attr(key, value)

    def remove_html_attr(self, key: str) -> None:
        self._check_disposed()
        assert self._root is not None
        return self._root.remove_html_attr(key)

    @property
    def html_attrs(self):
        self._check_disposed()
        assert self._root is not None
        return self._root.html_attrs

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        _active_app_context.reset(self._active_app_token)
        self._app._render_context_cv.reset(self._render_context_cv_token)
        _set_app_di_scope(None)
        _set_app_instance(None)
        di_scope = self._di_scope
        root = self._root
        assert di_scope is not None
        assert root is not None
        if self._di_scope_token is not None and di_scope._token is None:
            _active_di_scope.reset(self._di_scope_token)
        self._di_scope_token = None
        di_scope.__exit__(None, None, None)
        di_scope.dispose()
        root._head_element._cleanup_consumers()
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
        assert self._di_scope is not None
        return self._di_scope

    def provide(self, key: object, value: Any) -> None:
        self._check_disposed()
        assert self._di_scope is not None
        self._di_scope.provide(key, value)


class BrowserRenderContext(RenderContext):
    def _register_ports(self) -> None:
        from webcompy.ports._browser._async_scheduler import BrowserAsyncSchedulerPort
        from webcompy.ports._browser._cookie import BrowserCookiePort
        from webcompy.ports._browser._custom_element import BrowserCustomElementPort
        from webcompy.ports._browser._dom import BrowserDOMPort
        from webcompy.ports._browser._event_source import BrowserEventSourcePort
        from webcompy.ports._browser._fetch import BrowserFetchPort
        from webcompy.ports._browser._ffi import BrowserFFIPort
        from webcompy.ports._browser._history import BrowserHistoryPort
        from webcompy.ports._browser._host import BrowserHostPort
        from webcompy.ports._browser._media_query import BrowserMediaQueryPort
        from webcompy.ports._browser._resource import BrowserResourcePort
        from webcompy.ports._browser._transition import BrowserTransitionPort
        from webcompy.ports._browser._websocket import BrowserWebSocketPort
        from webcompy.ports._keys import (
            ASYNC_SCHEDULER_PORT_KEY,
            COOKIE_PORT_KEY,
            CUSTOM_ELEMENT_PORT_KEY,
            DOM_PORT_KEY,
            EVENT_SOURCE_PORT_KEY,
            FETCH_PORT_KEY,
            FFI_PORT_KEY,
            HISTORY_PORT_KEY,
            HOST_PORT_KEY,
            MARKDOWN_PORT_KEY,
            MEDIA_QUERY_PORT_KEY,
            RESOURCE_PORT_KEY,
            TRANSITION_PORT_KEY,
            WEBSOCKET_PORT_KEY,
        )
        from webcompy.template._markdown_default import DefaultMarkdownParser

        assert self._di_scope is not None
        router_mode = self._router.__mode__ if self._router else "history"
        self._di_scope.provide(ASYNC_SCHEDULER_PORT_KEY, BrowserAsyncSchedulerPort())
        self._di_scope.provide(COOKIE_PORT_KEY, BrowserCookiePort())
        self._di_scope.provide(CUSTOM_ELEMENT_PORT_KEY, BrowserCustomElementPort())
        self._di_scope.provide(DOM_PORT_KEY, BrowserDOMPort())
        self._di_scope.provide(EVENT_SOURCE_PORT_KEY, BrowserEventSourcePort())
        self._di_scope.provide(FETCH_PORT_KEY, BrowserFetchPort())
        self._di_scope.provide(RESOURCE_PORT_KEY, BrowserResourcePort(self._config.base_url))
        self._di_scope.provide(FFI_PORT_KEY, BrowserFFIPort())
        history_port = BrowserHistoryPort(mode=router_mode, base_url=self._config.base_url)
        self._di_scope.provide(HISTORY_PORT_KEY, history_port)
        host_port = BrowserHostPort()
        self._di_scope.provide(HOST_PORT_KEY, host_port)
        self._di_scope.provide(MEDIA_QUERY_PORT_KEY, BrowserMediaQueryPort())
        self._di_scope.provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        self._di_scope.provide(TRANSITION_PORT_KEY, BrowserTransitionPort())
        self._di_scope.provide(WEBSOCKET_PORT_KEY, BrowserWebSocketPort())

        if self._config.scroll_restoration and ENVIRONMENT == "pyscript":
            from webcompy.ports._browser._raw import browser as _raw_browser
            from webcompy.router._scroll import BrowserScrollManager

            assert _raw_browser is not None
            history_port.set_scroll_manager(BrowserScrollManager(host_port, _raw_browser.window))

        self._load_hydration_payload()

    def _load_hydration_payload(self) -> None:
        from webcompy.di._keys import (
            HYDRATION_DATA_KEY,
            HYDRATION_SIGNAL_DATA_KEY,
            RESOURCE_DATA_KEY,
        )
        from webcompy.hydration._payload import deserialize_payload
        from webcompy.ports._keys import DOM_PORT_KEY, FETCH_PORT_KEY

        assert self._di_scope is not None
        dom_port = self._di_scope.inject(DOM_PORT_KEY, default=None)
        if dom_port is None:
            return
        data_el = dom_port.query_selector("#__webcompy_data__")
        if data_el is None:
            return
        try:
            payload = deserialize_payload(str(data_el.textContent))
            if payload is not None:
                fetch_port = self._di_scope.inject(FETCH_PORT_KEY, default=None)
                if fetch_port is not None and hasattr(fetch_port, "populate_from_transfer"):
                    fetch_port.populate_from_transfer(payload.fetches)
                self._di_scope.provide(HYDRATION_DATA_KEY, payload.async_results)
                self._di_scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload.signals)
                self._di_scope.provide(RESOURCE_DATA_KEY, payload.resources)
        except Exception as exc:
            logging.getLogger(__name__).warning("Failed to load hydration payload: %s", exc)
        finally:
            data_el.remove()
