"""The ``WebComPyApp`` application object."""

from __future__ import annotations

import time
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Literal

from webcompy.aio import resolve_async
from webcompy.app._config import WebComPyAppConfig
from webcompy.components import ComponentGenerator
from webcompy.exception import WebComPyException
from webcompy.plugin._manager import PluginManager
from webcompy.router import Router
from webcompy.rpc._registry import ProcedureRegistry
from webcompy.utils import ENVIRONMENT

if TYPE_CHECKING:
    from webcompy.app._render_context import RenderContext
    from webcompy.signal import Computed


class WebComPyApp:
    """Application object bootstrapping the root component into the page.

    Owns the per-app configuration, router, plugin manager, and RPC
    registry. Head management and DI provisioning calls are forwarded to
    the active render context, or deferred until one is created. In the
    browser, ``run`` mounts and renders the root component at the
    configured selector.

    Args:
        root_component: Generator function producing the root component.
        router: Router defining the application's pages, when any.
        config: Application configuration (defaults to ``WebComPyAppConfig()``).
        _render_context_class: Render context class override, used for
            testing and server-side rendering.

    Attributes:
        config: The ``WebComPyAppConfig`` of this application.
        rpc: The ``ProcedureRegistry`` used to register RPC procedures.
        profile_data: Mapping of phase names to timestamps when profiling
            is enabled, ``None`` otherwise.
        di_scope: DI scope of the active render context; raises
            ``AttributeError`` without an active context.
        router: The configured ``Router``, or ``None`` when unset.
        routes: Routes of the active render context, falling back to the
            configured router's routes.
        router_mode: Router mode of the active render context, falling
            back to the configured router's mode.
        head: Reactive head data of the active render context.
        scoped_styles: Scoped styles collected by the active render
            context, keyed by component id.
        scripts: Script tuples appended through the active render context.
        html_attrs: Attributes managed on the document element; raises
            ``AttributeError`` without an active ``RenderContext``.

    """

    _config: WebComPyAppConfig
    _profile: bool
    _profile_data: dict[str, float]
    _render_context_cv: ContextVar[RenderContext | None]

    def __init__(
        self,
        *,
        root_component: ComponentGenerator[None],
        router: Router | None = None,
        config: WebComPyAppConfig | None = None,
        _render_context_class: type[RenderContext] | None = None,
    ) -> None:
        self._config = config or WebComPyAppConfig()
        self._profile = self._config.profile
        self._profile_data = {}
        # Defense-in-depth: the async scheduler port's drain mechanism provides the primary
        # structural guarantee that scheduled tasks complete before the render context is
        # disposed. This guard prevents hydration-related async scheduling from running on
        # the server even if the scheduler's drain mechanism were bypassed.
        self._hydrate = self._config.hydrate and ENVIRONMENT == "pyscript"
        self._render_context_cv = ContextVar(f"_render_context_cv_{id(self)}", default=None)
        self._root_component_def = root_component
        self._router = router
        self._router_pages = router.__routes__ if router else None
        self._router_mode: Literal["hash", "history"] = (
            router.__mode__ if router else "history"  # type: ignore[assignment]
        )
        self._router_base_url = router.__base_url__ if router else None
        self._component_generators: dict[str, ComponentGenerator[Any]] = {}
        self._deferred_ops: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self._plugin_manager = PluginManager(self)
        if self._config.plugins:
            self._plugin_manager.discover(self._config.plugins)
            self._plugin_manager.init_all()
        self._render_context_class = _render_context_class
        self._server_fetch_port: Any = None
        self._server_resource_port: Any = None
        self._ssg_full_text_resources: dict[str, bytes] | None = None
        self._rpc_registry = ProcedureRegistry(base_url=self._config.base_url)

    @property
    def config(self) -> WebComPyAppConfig:
        """Return the application configuration.

        Returns:
            The ``WebComPyAppConfig`` of this application.

        """
        return self._config

    @property
    def rpc(self) -> ProcedureRegistry:
        """Return the JSON-RPC procedure registry of this application.

        Returns:
            The ``ProcedureRegistry`` used to register RPC procedures.

        """
        return self._rpc_registry

    @property
    def profile_data(self) -> dict[str, float] | None:
        """Return per-phase timing data, available only when profiling is on.

        Returns:
            Mapping of phase names to ``time.perf_counter`` timestamps,
            or ``None`` when profiling is disabled.

        """
        return self._profile_data if self._profile else None

    def _record_phase(self, name: str) -> None:
        if self._profile and name not in self._profile_data:
            self._profile_data[name] = time.perf_counter()

    def _emit_profile_summary(self) -> None:
        if not self._profile:
            return
        data = self._profile_data
        pairs = [
            ("pyscript_ready", "imports_done", "pyscript_ready → imports_done"),
            ("imports_done", "init_done", "imports_done   → init_done"),
            ("init_done", "custom_elements_defined", "init_done      → custom_elements_defined"),
            ("custom_elements_defined", "run_done", "custom_elements_defined → run_done"),
            ("run_done", "loading_removed", "run_done       → loading_removed"),
            ("lazy_preload_start", "lazy_preloaded", "lazy_preload_start → lazy_preloaded"),
        ]
        lines = ["[WebComPy Profile]"]
        total = 0.0
        label_width = max(len(label) for _, _, label in pairs)
        for start_key, end_key, label in pairs:
            if start_key in data and end_key in data:
                elapsed = data[end_key] - data[start_key]
                if elapsed < 0:
                    continue
                total += elapsed
                lines.append(f"  {label.ljust(label_width)}: {elapsed:.3f}s")
        lines.append("  " + "─" * (label_width + 8))
        lines.append("  Total:".ljust(label_width + 4) + f"{total:.3f}s")
        output = "\n".join(lines)
        if ENVIRONMENT == "pyscript":
            from pyscript import context  # type: ignore[import-untyped]

            context.window.console.log(output)  # type: ignore[union-attr]
        else:
            print(output)

    def create_render_context(
        self,
        path: str | None = None,
        *,
        initial_theme: Any = None,
        cookie_header: str | None = None,
    ) -> RenderContext:
        """Create a render context and make it the active one for this application.

        Args:
            path: Initial route path to open in the created context.
            initial_theme: Initial theme override for the created context.
            cookie_header: Raw ``Cookie`` header value used to resolve the
                initial theme.

        Returns:
            The newly created render context.

        """
        from webcompy.app._render_context import BrowserRenderContext

        cls = self._render_context_class or BrowserRenderContext
        ctx = cls(
            self,
            path,
            initial_theme=initial_theme,
            cookie_header=cookie_header,
        )
        self._render_context_cv.set(ctx)
        return ctx

    def _apply_deferred_ops(self, ctx: RenderContext) -> None:
        for method_name, args, kwargs in self._deferred_ops:
            getattr(ctx, method_name)(*args, **kwargs)

    @property
    def di_scope(self):
        """Return the DI scope of the active render context.

        Returns:
            The active ``DIScope``.

        Raises:
            AttributeError: When no render context is active.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.di_scope
        raise AttributeError(
            "WebComPyApp.di_scope is not available without a RenderContext. "
            "Use app.create_render_context(path) or call app.run() in the browser."
        )

    def provide(self, key: object, value: Any) -> None:
        """Provide a value in the app DI scope, deferring until a render context exists.

        Args:
            key: Injection key the value is registered under.
            value: Value provided under ``key``.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            ctx.provide(key, value)
            return
        self._deferred_ops.append(("provide", (key, value), {}))

    @property
    def router(self):
        """Return the router configured on this application.

        Returns:
            The ``Router`` of this application, or ``None`` when unset.

        """
        return self._router

    @property
    def routes(self):
        """Return the routes of the active render context, falling back to the configured router.

        Returns:
            The routes of the active context when one exists, otherwise
            the routes of the configured router (or ``None``).

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.routes
        return self._router_pages

    @property
    def router_mode(self):
        """Return the router mode of the active render context, falling back to the configured router.

        Returns:
            The router mode of the active context when one exists,
            otherwise the mode of the configured router.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.router_mode
        return self._router_mode

    def set_path(self, path: str):
        """Change the active route path.

        Args:
            path: The new route path.

        Returns:
            The result of the underlying navigation, or ``None`` when no
            context exists in the browser.

        Raises:
            AttributeError: When called on the server without an active
                render context.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.set_path(path)
        if ENVIRONMENT == "pyscript":
            return None
        raise AttributeError(
            "WebComPyApp.set_path() is not available on the server. "
            "Use RenderContext.set_path() instead via app.create_render_context(path)."
        )

    @property
    def head(self):
        """Return the head data of the active render context.

        Returns:
            The reactive head data of the active context.

        Raises:
            AttributeError: When no render context is active.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.head
        raise AttributeError("WebComPyApp.head is not available without a RenderContext.")

    @property
    def scoped_styles(self):
        """Return the scoped styles collected by the active render context.

        Returns:
            Mapping of component ids to their scoped CSS rules.

        Raises:
            AttributeError: When no render context is active.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.scoped_styles
        raise AttributeError("WebComPyApp.scoped_styles is not available without a RenderContext.")

    @property
    def scripts(self):
        """Return the scripts appended by the active render context.

        Returns:
            List of script tuples appended through the active context.

        Raises:
            AttributeError: When no render context is active.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.scripts
        raise AttributeError("WebComPyApp.scripts is not available without a RenderContext.")

    def set_title(self, title: str) -> None:
        """Set the document title, deferring the call until a render context exists.

        Args:
            title: The document title to set.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.set_title(title)
        self._deferred_ops.append(("set_title", (title,), {}))

    def set_meta(self, key: str, attributes: dict[str, str]) -> None:
        """Add or replace a meta tag, deferring the call until a render context exists.

        Args:
            key: Identifier of the meta tag.
            attributes: HTML attributes of the meta tag.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.set_meta(key, attributes)
        self._deferred_ops.append(("set_meta", (key, attributes), {}))

    def append_link(self, attributes: dict[str, str]) -> None:
        """Append a link element to the head, deferring the call until a render context exists.

        Args:
            attributes: HTML attributes of the link element.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.append_link(attributes)
        self._deferred_ops.append(("append_link", (attributes,), {}))

    def append_script(
        self,
        attributes: dict[str, str],
        script: str | None = None,
        in_head: bool = False,
    ) -> None:
        """Append a script element, deferring the call until a render context exists.

        Args:
            attributes: HTML attributes of the script element.
            script: Inline script body when the script is inlined.
            in_head: Whether the script goes in ``<head>`` instead of ``<body>``.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.append_script(attributes, script, in_head)
        self._deferred_ops.append(("append_script", (attributes, script, in_head), {}))

    def set_head(self, head: Any) -> None:
        """Replace the head VDOM, deferring the call until a render context exists.

        Args:
            head: The new head data.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.set_head(head)
        self._deferred_ops.append(("set_head", (head,), {}))

    def update_head(self, head: Any) -> None:
        """Merge data into the head VDOM, deferring the call until a render context exists.

        Args:
            head: Head data merged into the current head.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.update_head(head)
        self._deferred_ops.append(("update_head", (head,), {}))

    def set_html_attr(self, key: str, value: Any) -> None:
        """Set an attribute on the document element, deferring the call until a render context exists.

        Args:
            key: Attribute name.
            value: Attribute value.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.set_html_attr(key, value)
        self._deferred_ops.append(("set_html_attr", (key, value), {}))

    def remove_html_attr(self, key: str) -> None:
        """Remove an attribute from the document element, deferring the call until a render context exists.

        Args:
            key: Attribute name.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.remove_html_attr(key)
        self._deferred_ops.append(("remove_html_attr", (key,), {}))

    def append_style(self, content: str | Computed[str]) -> None:
        """Inject an app-level style, deferring the call until a render context exists.

        Args:
            content: CSS content, or a reactive ``Computed`` producing it.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            ctx.append_style(content)
            return
        self._deferred_ops.append(("append_style", (content,), {}))

    @property
    def html_attrs(self):
        """Return the attributes managed on the document element.

        Returns:
            The html attributes of the active context.

        Raises:
            AttributeError: When no render context is active.

        """
        ctx = self._render_context_cv.get()
        if ctx is not None:
            return ctx.html_attrs
        raise AttributeError("WebComPyApp.html_attrs is not available without a RenderContext.")

    def run(self) -> None:
        """Mount and render the application in the browser.

        Raises:
            WebComPyException: When called outside a browser (PyScript) environment.

        """
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("app.run() can only be called in a browser environment.")
        self._record_phase("run_start")
        ctx = self.create_render_context()
        self._plugin_manager.call_on_app_ready(ctx)

        assert ctx._root is not None
        ctx._root._selector = self._config.selector
        resolve_async(ctx._root._render())
