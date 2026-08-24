"""Per-render context abstraction: ``RenderContext`` and its browser implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from webcompy.app._config import WebComPyAppConfig
from webcompy.components._component import (
    _active_app_context,
    _get_app_instance,
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
from webcompy.di._scope import (
    DIScope,
    _active_di_scope,
    _get_app_di_scope,
    _set_app_di_scope,
)
from webcompy.elements.types._teleport import _TeleportTargetRegistry
from webcompy.exception import WebComPyException
from webcompy.hydration._report import HydrationMismatchRecord, HydrationReporter
from webcompy.router import Router
from webcompy.utils import ENVIRONMENT

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp
    from webcompy.app._root_component import AppDocumentRoot


class RenderContext(ABC):
    """Per-render context encapsulating one application render operation.

    Owns the DI scope, component store, router clone, and document root
    used for a single render. Head management and HTML mutation calls are
    forwarded to the document root, and ``dispose`` releases all bound
    resources. ``BrowserRenderContext`` is the default implementation;
    server deployments provide their own subclass for SSR/SSG.

    Args:
        app: Application this context renders for.
        path: Initial route path to open.
        initial_theme: Initial theme override.
        cookie_header: Raw ``Cookie`` header used to resolve the initial
            theme.

    Attributes:
        hydration_report: Hydration mismatch records collected during
            this render.
        routes: Routes exposed by the context's router, or ``None``
            when there is no router.
        router_mode: Mode of the context's router, or ``None`` when
            there is no router.
        head: Reactive head data aggregated for this context.
        scoped_styles: Scoped styles registered through this context,
            keyed by component id.
        scripts: Script tuples appended through this context.
        html_attrs: Document-level attributes managed by this context.
        config: The application configuration this context renders with.
        di_scope: The context's ``DIScope``.

    """

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
        self._disposed = False
        self._defer_depth: int = 0
        self._deferred_callbacks: list = []
        self._hydration_in_progress: bool = False
        self._hydration_payload_closed: bool = False
        self._hydration_reporter = HydrationReporter()
        self._transfer_ordinal_counters: dict[str, int] = {}
        self._transfer_probe_depth: int = 0
        self._prev_app_instance: Any = None
        self._prev_app_di_scope: DIScope | None = None
        self._prev_active_app_context: Any = None
        self._prev_render_context_cv: Any = None
        self._prev_active_di_scope: DIScope | None = None
        self._initial_theme = initial_theme
        self._cookie_header = cookie_header or ""

        app._record_phase("init_start")

        self._di_scope = DIScope()
        self._component_store = ComponentStore()
        self._di_scope.provide(_APP_KEY, app)
        self._di_scope.provide(_COMPONENT_STORE_KEY, self._component_store)
        self._di_scope.provide(RPC_REGISTRY_KEY, app._rpc_registry)
        self._di_scope.provide(_TELEPORT_REGISTRY_KEY, _TeleportTargetRegistry())

        self._router = None
        if app._router:
            self._router = app._router._clone_for_request()

        self._prev_active_di_scope = _active_di_scope.get(None)
        self._di_scope.__enter__()
        self._di_scope_token = self._di_scope._token

        self._prev_active_app_context = _active_app_context.get()
        self._active_app_token = _active_app_context.set(self)
        self._prev_render_context_cv = self._app._render_context_cv.get()
        self._render_context_cv_token = self._app._render_context_cv.set(self)

        if ENVIRONMENT == "pyscript":
            self._prev_app_instance = _get_app_instance()
            self._prev_app_di_scope = _get_app_di_scope()
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

        self._app._record_phase("imports_done")

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

        self._app._record_phase("init_done")

    @abstractmethod
    def _register_ports(self) -> None: ...

    async def render_html(self, **kwargs: Any) -> str:
        """Render the document into an HTML string.

        Args:
            **kwargs: Keyword arguments forwarded through the render pipeline.

        Returns:
            The generated HTML string.

        Raises:
            WebComPyException: Always, because the browser context cannot
                produce an HTML string.

        """
        raise WebComPyException("render_html() is not available in the browser render context")

    @property
    def hydration_report(self) -> tuple[HydrationMismatchRecord, ...]:
        """Return the hydration mismatch records collected during this render.

        Returns:
            Tuple of hydration mismatch records.

        """
        return tuple(self._hydration_reporter.records)

    @property
    def routes(self):
        """Return the routes of this context.

        Returns:
            The routes exposed by the context's router, or ``None`` when
            there is no router.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.routes

    @property
    def router_mode(self):
        """Return the router mode of this context.

        Returns:
            The mode of the context's router, or ``None`` when there is
            no router.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.router_mode

    def set_path(self, path: str):
        """Open the given route path.

        Args:
            path: The route path to open.

        Returns:
            The result of the underlying navigation of the document root.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.set_path(path)

    @property
    def head(self):
        """Return the reactive head data of the document.

        Returns:
            The head data aggregated for this context.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.head

    @property
    def scoped_styles(self):
        """Return the scoped styles registered through this context.

        Returns:
            Mapping of component ids to their scoped CSS rules.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.scoped_styles

    @property
    def scripts(self):
        """Return the scripts appended to the document body.

        Returns:
            List of script tuples appended through this context.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.scripts

    def set_title(self, title: str) -> None:
        """Set the document title.

        Args:
            title: The document title to set.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.set_title(title)

    def set_meta(self, key: str, attributes: dict[str, str]) -> None:
        """Add or replace a meta tag in the document head.

        Args:
            key: Identifier of the meta tag.
            attributes: HTML attributes of the meta tag.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.set_meta(key, attributes)

    def append_link(self, attributes: dict[str, str]) -> None:
        """Append a link element to the document head.

        Args:
            attributes: HTML attributes of the link element.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.append_link(attributes)

    def append_script(
        self,
        attributes: dict[str, str],
        script: str | None = None,
        in_head: bool = False,
    ) -> None:
        """Append a script element.

        Args:
            attributes: HTML attributes of the script element.
            script: Inline script body when the script is inlined.
            in_head: Whether the script goes in ``<head>`` instead of ``<body>``.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.append_script(attributes, script, in_head)

    def append_style(self, content: Any) -> None:
        """Inject an app-level style.

        Args:
            content: CSS content, or a reactive ``Computed`` producing it.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.append_style(content)

    def set_head(self, head: Any) -> None:
        """Replace the head VDOM of the document.

        Args:
            head: The new head data.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.set_head(head)

    def update_head(self, head: Any) -> None:
        """Merge data into the head VDOM of the document.

        Args:
            head: Head data merged into the current head.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.update_head(head)

    def set_html_attr(self, key: str, value: Any) -> None:
        """Set an attribute on the document element.

        Args:
            key: Attribute name.
            value: Attribute value.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.set_html_attr(key, value)

    def remove_html_attr(self, key: str) -> None:
        """Remove an attribute from the document element.

        Args:
            key: Attribute name.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.remove_html_attr(key)

    @property
    def html_attrs(self):
        """Return the attributes managed on the document element.

        Returns:
            The document-level attributes of this context.

        """
        self._check_disposed()
        assert self._root is not None
        return self._root.html_attrs

    def dispose(self) -> None:
        """Release all resources bound to this render context.

        Restores any previously active contexts, exits and disposes the
        DI scope, and cleans up head consumers. Calling ``dispose`` more
        than once is a no-op.

        """
        if self._disposed:
            return
        self._disposed = True

        def _next_live_ctx(start):
            cur = start
            while cur is not None and getattr(cur, "_disposed", False):
                nxt = getattr(cur, "_prev_active_app_context", None)
                if nxt is None:
                    nxt = getattr(cur, "_prev_app_instance", None)
                cur = nxt
            return cur

        def _next_live_render_ctx(start):
            cur = start
            while cur is not None and getattr(cur, "_disposed", False):
                nxt = getattr(cur, "_prev_render_context_cv", None)
                if nxt is None:
                    nxt = getattr(cur, "_prev_app_instance", None)
                cur = nxt
            return cur

        def _find_next_live_di(start_ctx):
            cur = start_ctx
            while cur is not None:
                di = getattr(cur, "_prev_active_di_scope", None)
                if di is not None and not getattr(di, "_disposed", False):
                    return di
                if not getattr(cur, "_disposed", False):
                    di = getattr(cur, "_di_scope", None)
                    if di is not None and not getattr(di, "_disposed", False):
                        return di
                nxt = getattr(cur, "_prev_active_app_context", None) or getattr(cur, "_prev_app_instance", None)
                cur = nxt
            return None

        if _active_app_context.get() is self:
            _active_app_context.reset(self._active_app_token)
            cur = _active_app_context.get()
            live = _next_live_ctx(cur)
            if live is not cur:
                _active_app_context.set(live)
        if self._app._render_context_cv.get() is self:
            self._app._render_context_cv.reset(self._render_context_cv_token)
            cur = self._app._render_context_cv.get()
            live = _next_live_render_ctx(cur)
            if live is not cur:
                self._app._render_context_cv.set(live)
        self._restore_browser_fallback()
        di_scope = self._di_scope
        root = self._root
        assert di_scope is not None
        assert root is not None
        active_di = _active_di_scope.get(None)
        node = active_di
        while node is not None and node is not di_scope:
            node = getattr(node, "_parent", None)
        if node is not None and self._di_scope_token is not None:
            try:
                _active_di_scope.reset(self._di_scope_token)
            except (RuntimeError, ValueError):
                _active_di_scope.set(None)  # type: ignore[arg-type]
            cur_di = _active_di_scope.get(None)
            if cur_di is not None and getattr(cur_di, "_disposed", False):
                live_di = _find_next_live_di(self._prev_active_app_context)
                _active_di_scope.set(live_di)  # type: ignore[arg-type]
        self._di_scope_token = None
        if di_scope._token is not None:
            di_scope._token = None
        di_scope.__exit__(None, None, None)
        di_scope.dispose()
        root._head_element._cleanup_consumers()
        self._root = None
        self._di_scope = None
        self._component_store = None
        self._router = None

    def _restore_browser_fallback(self) -> None:
        """Restore the previous PyScript fallback when disposing the current one.

        The module-level app fallbacks (``_app_instance`` / ``_app_di_scope``)
        hold only the most recently created context. When a context that is no
        longer the current fallback is disposed, the surviving fallback is left
        untouched. When the disposed context IS the current fallback, the
        previously registered context (walking past any already-disposed
        contexts) is restored so overlapping browser contexts keep working after
        disposal in any order.
        """
        if _get_app_instance() is not self:
            return
        candidate = self._prev_app_instance
        candidate_scope = self._prev_app_di_scope
        while candidate is not None and getattr(candidate, "_disposed", False):
            candidate_scope = candidate._prev_app_di_scope
            candidate = candidate._prev_app_instance
        _set_app_instance(candidate)
        _set_app_di_scope(candidate_scope)

    def _check_disposed(self) -> None:
        if self._disposed:
            raise RuntimeError("RenderContext has been disposed")

    @property
    def config(self) -> WebComPyAppConfig:
        """Return the application configuration.

        Returns:
            The ``WebComPyAppConfig`` of the application.

        """
        return self._config

    def _next_transfer_id(self, component_name: str) -> str:
        from webcompy.components._libs import generate_id

        if self._transfer_probe_depth > 0:
            return generate_id(component_name)
        ordinal = self._transfer_ordinal_counters.get(component_name, 0)
        self._transfer_ordinal_counters[component_name] = ordinal + 1
        return f"{generate_id(component_name)}#{ordinal}"

    @property
    def di_scope(self) -> DIScope:
        """Return the DI scope of this context.

        Returns:
            The ``DIScope`` owning this context's provided values.

        """
        self._check_disposed()
        assert self._di_scope is not None
        return self._di_scope

    def provide(self, key: object, value: Any) -> None:
        """Provide a value in the DI scope of this context.

        Args:
            key: Injection key the value is registered under.
            value: Value provided under ``key``.

        """
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
