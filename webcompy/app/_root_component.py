from __future__ import annotations

from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, TypedDict

from webcompy.components._component import Component, HeadPropsStore
from webcompy.components._generator import ComponentGenerator
from webcompy.di import inject
from webcompy.di._keys import _HEAD_PROPS_KEY, _ROUTER_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.elements._dom_objs import DOMNode
from webcompy.elements._head import HeadElement
from webcompy.ports._keys import DOM_PORT_KEY
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

        with di_scope:
            super().__init__(_root_template, None, {"root": lambda: root_component(None)})

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
            for child in self._children:
                await child._hydrate_node()

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
                if self.__loading:
                    self.__loading = False
                    selector = self._selector or (self._app.config.selector if self._app else "#webcompy-app")
                    loading_el = _dom.query_selector(f"{selector} > #webcompy-loading") or _dom.get_element_by_id(
                        "webcompy-loading"
                    )
                    if loading_el:
                        loading_el.remove()
                    if self._router and self._router._preload:
                        self._router.preload_lazy_routes()
                    if self._app:
                        self._app._record_phase("loading_removed")
                        self._app._emit_profile_summary()
        finally:
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
                if name != "id" and not name.startswith("webcompy"):
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
