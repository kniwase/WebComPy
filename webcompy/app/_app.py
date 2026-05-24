from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from webcompy.app._config import WebComPyAppConfig
from webcompy.components import ComponentGenerator
from webcompy.exception import WebComPyException
from webcompy.plugin._manager import PluginManager
from webcompy.router import Router
from webcompy.utils import ENVIRONMENT

if TYPE_CHECKING:
    from webcompy.app._render_context import RenderContext


class WebComPyApp:
    _config: WebComPyAppConfig
    _profile: bool
    _render_context: RenderContext | None

    def __init__(
        self,
        *,
        root_component: ComponentGenerator[None],
        router: Router | None = None,
        config: WebComPyAppConfig | None = None,
    ) -> None:
        self._config = config or WebComPyAppConfig()
        self._profile = self._config.profile
        self._hydrate = self._config.hydrate
        self._render_context = None
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

    @property
    def config(self) -> WebComPyAppConfig:
        return self._config

    @property
    def profile_data(self) -> dict[str, float] | None:
        if self._render_context is not None:
            return self._render_context.profile_data
        return None

    def _record_phase(self, name: str) -> None:
        if self._render_context is not None:
            self._render_context._record_phase(name)

    def _emit_profile_summary(self) -> None:
        if not self._profile:
            return
        ctx = self._render_context
        if ctx is None:
            return
        data = ctx._profile_data
        pairs = [
            ("pyscript_ready", "imports_done", "pyscript_ready → imports_done"),
            ("imports_done", "init_done", "imports_done   → init_done"),
            ("init_done", "run_start", "init_done      → run_start"),
            ("run_start", "run_done", "run_start      → run_done"),
            ("run_done", "loading_removed", "run_done       → loading_removed"),
        ]
        lines = ["[WebComPy Profile]"]
        total = 0.0
        label_width = max(len(label) for _, _, label in pairs)
        for start_key, end_key, label in pairs:
            if start_key in data and end_key in data:
                elapsed = data[end_key] - data[start_key]
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

    def create_render_context(self, path: str | None = None) -> RenderContext:
        from webcompy.app._render_context import RenderContext

        ctx = RenderContext(self, path)
        self._render_context = ctx
        return ctx

    def _apply_deferred_ops(self, ctx: RenderContext) -> None:
        for method_name, args, kwargs in self._deferred_ops:
            getattr(ctx, method_name)(*args, **kwargs)

    @property
    def di_scope(self):
        if self._render_context is not None:
            return self._render_context.di_scope
        raise AttributeError(
            "WebComPyApp.di_scope is not available without a RenderContext. "
            "Use app.create_render_context(path) or call app.run() in the browser."
        )

    def provide(self, key: object, value: Any) -> None:
        if self._render_context is not None:
            self._render_context.provide(key, value)
            return
        self._deferred_ops.append(("provide", (key, value), {}))

    @property
    def router(self):
        return self._router

    @property
    def routes(self):
        if self._render_context is not None:
            return self._render_context.routes
        return self._router_pages

    @property
    def router_mode(self):
        if self._render_context is not None:
            return self._render_context.router_mode
        return self._router_mode

    def set_path(self, path: str):
        if self._render_context is not None:
            return self._render_context.set_path(path)
        if ENVIRONMENT == "pyscript":
            return None
        raise AttributeError(
            "WebComPyApp.set_path() is not available on the server. "
            "Use RenderContext.set_path() instead via app.create_render_context(path)."
        )

    @property
    def head(self):
        if self._render_context is not None:
            return self._render_context.head
        raise AttributeError("WebComPyApp.head is not available without a RenderContext.")

    @property
    def style(self):
        if self._render_context is not None:
            return self._render_context.style
        raise AttributeError("WebComPyApp.style is not available without a RenderContext.")

    @property
    def scripts(self):
        if self._render_context is not None:
            return self._render_context.scripts
        raise AttributeError("WebComPyApp.scripts is not available without a RenderContext.")

    def set_title(self, title: str) -> None:
        if self._render_context is not None:
            return self._render_context.set_title(title)
        self._deferred_ops.append(("set_title", (title,), {}))

    def set_meta(self, key: str, attributes: dict[str, str]) -> None:
        if self._render_context is not None:
            return self._render_context.set_meta(key, attributes)
        self._deferred_ops.append(("set_meta", (key, attributes), {}))

    def append_link(self, attributes: dict[str, str]) -> None:
        if self._render_context is not None:
            return self._render_context.append_link(attributes)
        self._deferred_ops.append(("append_link", (attributes,), {}))

    def append_script(
        self,
        attributes: dict[str, str],
        script: str | None = None,
        in_head: bool = False,
    ) -> None:
        if self._render_context is not None:
            return self._render_context.append_script(attributes, script, in_head)
        self._deferred_ops.append(("append_script", (attributes, script, in_head), {}))

    def set_head(self, head: Any) -> None:
        if self._render_context is not None:
            return self._render_context.set_head(head)
        self._deferred_ops.append(("set_head", (head,), {}))

    def update_head(self, head: Any) -> None:
        if self._render_context is not None:
            return self._render_context.update_head(head)
        self._deferred_ops.append(("update_head", (head,), {}))

    def set_html_attr(self, key: str, value: Any) -> None:
        if self._render_context is not None:
            return self._render_context.set_html_attr(key, value)
        self._deferred_ops.append(("set_html_attr", (key, value), {}))

    def remove_html_attr(self, key: str) -> None:
        if self._render_context is not None:
            return self._render_context.remove_html_attr(key)
        self._deferred_ops.append(("remove_html_attr", (key,), {}))

    @property
    def html_attrs(self):
        if self._render_context is not None:
            return self._render_context.html_attrs
        raise AttributeError("WebComPyApp.html_attrs is not available without a RenderContext.")

    def run(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("app.run() can only be called in a browser environment.")
        self._record_phase("run_start")
        from webcompy.components._component import _active_app_context, _set_app_instance

        ctx = self.create_render_context()
        self._render_context = ctx
        _active_app_context.set(ctx)
        _set_app_instance(ctx)
        self._plugin_manager.call_on_app_ready(ctx)
        ctx._root._selector = self._config.selector
        ctx._root.render()
