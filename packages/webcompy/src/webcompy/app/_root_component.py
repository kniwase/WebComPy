from __future__ import annotations

import asyncio
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, TypedDict

from webcompy.app._config import _LOADING_INT_KEY_MAX
from webcompy.components._component import Component, HeadPropsStore, _active_app_context
from webcompy.components._generator import ComponentGenerator
from webcompy.di import inject
from webcompy.di._keys import _HEAD_PROPS_KEY, _ROUTER_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.elements._dom_objs import DOMNode
from webcompy.elements._head import HeadElement
from webcompy.hydration._collect import collect_transfer_data
from webcompy.hydration._payload import DEFAULT_COMPRESSION_THRESHOLD, serialize_payload
from webcompy.hydration._report import emit_report_summary
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, DOM_PORT_KEY
from webcompy.router._keys import RouterKey
from webcompy.router._router import Router
from webcompy.signal import Computed
from webcompy.utils import ENVIRONMENT

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp


class Head(TypedDict, total=False):
    title: str
    meta: dict[str, dict[str, str]]
    link: list[dict[str, str]]
    script: list[tuple[dict[str, str], str | None]]


class HeadSignal(TypedDict):
    title: Computed[str | None]
    meta: Computed[dict[str, dict[str, str]]]
    link: list[dict[str, str]]
    script: list[tuple[dict[str, str], str | None]]


class AppDocumentRoot(Component):
    _router: Router | None
    __loading: bool
    __hydrated: bool

    def __init__(
        self,
        root_component: ComponentGenerator[None],
        router: Router | None,
        di_scope: DIScope,
        selector: str | None = None,
        app: WebComPyApp | None = None,
    ) -> None:
        self.__loading = True
        self.__hydrated = False
        self._router = router
        self._di_scope = di_scope
        self._selector = selector
        self._app = app

        _mount_id = (app.config.selector.lstrip("#") if app else None) or (
            selector.lstrip("#") if selector else "webcompy-app"
        )

        def _root_template(context):
            return html.DIV({"id": _mount_id}, context.slots("root"))

        _root_template.__webcompy_component_definition__ = True

        head_props = HeadPropsStore()
        self._head_props = head_props
        di_scope.provide(_HEAD_PROPS_KEY, head_props)
        if self._router:
            di_scope.provide(_ROUTER_KEY, self._router)
            di_scope.provide(RouterKey, self._router)
        self._scripts: list[tuple[dict[str, str], str | None]] = []
        self._head_element = HeadElement(head_props)

        if _active_di_scope.get(None) is di_scope:
            super().__init__(_root_template, None, {"root": lambda: root_component(None)})
        else:
            token = _active_di_scope.set(di_scope)
            try:
                super().__init__(_root_template, None, {"root": lambda: root_component(None)})
            finally:
                _active_di_scope.reset(token)

    @property
    def render(self):
        return self._render

    async def _render(self):
        token = _active_di_scope.set(self._di_scope)
        try:
            on_before = self._property["on_before_rendering"]
            if iscoroutinefunction(on_before):
                await on_before()
            else:
                on_before()
            self._mount_node()
            if self._app and self._app._hydrate and not self.__hydrated:
                self.__hydrated = True
                ctx = _active_app_context.get()
                if ctx is not None:
                    ctx._hydration_in_progress = True
                self._ensure_custom_elements_defined()
                for child in self._children:
                    child._hydrate_node()

            for child in self._children:
                await child._render()

            on_after = self._property["on_after_rendering"]
            if iscoroutinefunction(on_after):
                await on_after()
            else:
                on_after()
            if self._app:
                self._app._record_phase("run_done")
            if ENVIRONMENT == "pyscript":
                _dom = inject(DOM_PORT_KEY)
                await self._head_element._render()
                ctx = _active_app_context.get()
                if ctx is not None and self._app and self._app._hydrate:
                    scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
                    await scheduler.await_pending(only_render=True)
                    ctx._hydration_in_progress = False
                    ctx._hydration_payload_closed = True
                    emit_report_summary(ctx)
                if self.__loading:
                    self.__loading = False
                    selector = self._selector or (self._app.config.selector if self._app else "#webcompy-app")
                    loading_el = _dom.query_selector(f"{selector} > #webcompy-loading") or _dom.get_element_by_id(
                        "webcompy-loading"
                    )
                    if loading_el:
                        fade_ms = _loading_fade_ms(loading_el, self._app)
                        loading_el.setAttribute("data-wc-complete", "")
                        cls = (loading_el.getAttribute("class") or "").strip()
                        loading_el.setAttribute("class", f"{cls} wc-fading".strip())
                        body_el = _dom.query_selector("body")
                        if body_el is not None:
                            body_cls = body_el.getAttribute("class") or ""
                            if "wc-booting" in body_cls.split():
                                body_el.setAttribute("class", body_cls.replace("wc-booting", "wc-waking"))
                        mount_el = _dom.query_selector(selector)
                        if mount_el is not None:
                            mount_el.removeAttribute("aria-busy")
                            mount_el.removeAttribute("inert")
                        await asyncio.sleep(fade_ms / 1000)
                        loading_el.remove()
                        if body_el is not None:
                            body_cls = body_el.getAttribute("class") or ""
                            if "wc-waking" in body_cls.split():
                                wake_wait = _loading_wake_remaining_ms(fade_ms)
                                if wake_wait > 0:
                                    await asyncio.sleep(wake_wait / 1000)
                                    body_cls = body_el.getAttribute("class") or ""
                            remaining = " ".join(c for c in body_cls.split() if c != "wc-waking")
                            if remaining != body_cls:
                                if remaining:
                                    body_el.setAttribute("class", remaining)
                                else:
                                    body_el.removeAttribute("class")
                    if self._router and self._router._preload:
                        self._router.preload_lazy_routes()
                    if self._app:
                        self._app._record_phase("loading_removed")
                        self._app._emit_profile_summary()
        finally:
            ctx = _active_app_context.get()
            if ctx is not None:
                ctx._hydration_in_progress = False
                ctx._hydration_payload_closed = True
            if ENVIRONMENT != "pyscript":
                _active_di_scope.reset(token)

    def _init_node(self) -> DOMNode:
        selector = self._selector or (self._app.config.selector if self._app else "#webcompy-app")
        if ENVIRONMENT == "pyscript":
            node = inject(DOM_PORT_KEY).query_selector(selector)
            if node is None:
                from webcompy.exception import WebComPyException as _WCE

                raise _WCE(f"Mount point '{selector}' not found in document.")
            for name in tuple(node.getAttributeNames()):
                if name not in ("id", "aria-busy", "inert") and not name.startswith("webcompy"):
                    node.removeAttribute(name)
            node.__webcompy_node__ = True
            self._mark_as_prerendered(node)
            return node
        else:
            mount_id = selector.lstrip("#")
            node = inject(DOM_PORT_KEY).create_element("div")
            node.setAttribute("id", mount_id)
            node.__webcompy_node__ = True
            return node

    def _mark_as_prerendered(self, node: DOMNode):
        node.__webcompy_prerendered_node__ = True
        for child in getattr(node, "childNodes", []):
            self._mark_as_prerendered(child)

    def _ensure_custom_elements_defined(self) -> None:
        from webcompy.di import inject
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        store = inject(_COMPONENT_STORE_KEY, default=None)
        port = inject(CUSTOM_ELEMENT_PORT_KEY, default=None)
        if store is None or port is None:
            return
        for generator in store.components.values():
            port.ensure_defined(
                generator.custom_element_name,
                generator.observed_attributes,
                generator.definition_key,
            )

    def _mount_node(self):
        if ENVIRONMENT == "pyscript":
            return
        super()._mount_node()

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self) -> tuple[Component, ...]:
        return (self,)

    @property
    def routes(self):
        return self._router.__routes__ if self._router else None

    @property
    def router_mode(self):
        return self._router.__mode__ if self._router else None

    def set_path(self, path: str):
        if self._router:
            self._router.__set_path__(path, None)
        else:
            return None

    @property
    def scoped_styles(self):
        from webcompy.di import inject
        from webcompy.di._keys import _COMPONENT_STORE_KEY

        store = inject(_COMPONENT_STORE_KEY)
        result: dict[str, str] = {}
        for _name, component in sorted(store.components.items()):
            style = component.scoped_style
            if style:
                result[component._id] = style
        return result

    def set_html_attr(self, key: str, value: str | Computed[str]):
        self._head_element.set_html_attr(key, value)

    def remove_html_attr(self, key: str):
        self._head_element.remove_html_attr(key)

    @property
    def html_attrs(self) -> dict[str, str]:
        return self._head_element.html_attrs

    def set_title(self, title: str):
        self._head_element.set_title(title)

    def set_meta(self, key: str, attributes: dict[str, str]):
        self._head_element.set_meta(key, attributes)

    def append_link(self, attributes: dict[str, str]):
        self._head_element.append_link(attributes)

    def append_script(
        self,
        attributes: dict[str, str],
        script: str | None = None,
        in_head: bool = False,
    ):
        if not in_head:
            self._scripts.append((attributes, script))
        else:
            self._head_element.append_script(attributes, script)

    def append_style(self, content: Any) -> None:
        self._head_element.append_style(content)

    def set_head(self, head: Head):
        self._head_element.set_head(head)

    def update_head(self, head: Head):
        self._head_element.update_head(head)

    @property
    def head(self) -> HeadSignal:
        return self._head_element.head_data  # type: ignore[return-value]

    @property
    def scripts(self):
        return self._scripts

    def _collect_transfer_data(self) -> str:
        payload = collect_transfer_data(self)
        threshold = self._app.config.compression_threshold if self._app else DEFAULT_COMPRESSION_THRESHOLD
        return serialize_payload(payload, compression_threshold=threshold)


def _loading_fade_ms(loading_el: DOMNode, app: WebComPyApp | None) -> int:
    attr = loading_el.getAttribute("data-wc-fade")
    if attr:
        try:
            return min(_LOADING_INT_KEY_MAX["fade_out_ms"], max(0, int(attr)))
        except ValueError:
            pass
    if app is not None:
        return int((app.config.loading or {}).get("fade_out_ms", 250))
    return 250


_LOADING_WAKE_MS = 300


def _loading_wake_remaining_ms(fade_ms: int) -> int:
    return max(0, _LOADING_WAKE_MS - fade_ms)
