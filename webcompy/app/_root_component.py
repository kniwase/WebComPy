from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from webcompy.components._component import Component, HeadPropsStore, _active_app_context
from webcompy.components._generator import ComponentGenerator
from webcompy.di import inject
from webcompy.di._keys import _HEAD_PROPS_KEY, _ROUTER_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.elements._dom_objs import DOMNode
from webcompy.ports._keys import DOM_PORT_KEY
from webcompy.router._keys import RouterKey
from webcompy.router._router import Router
from webcompy.signal import Computed
from webcompy.signal._graph import consumer_destroy
from webcompy.utils import ENVIRONMENT

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp
    from webcompy.signal._base import CallbackConsumerNode


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
    _links: list[dict[str, str]]
    _scripts: list[tuple[dict[str, str], str | None]]
    _scripts_head: list[tuple[dict[str, str], str | None]]
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
        if ENVIRONMENT == "pyscript":

            def updte_title(title: str | None):
                if title is not None:
                    inject(DOM_PORT_KEY).set_title(title)

            head_props.title.on_after_updating(updte_title)

        head_props._app_title = ""
        self._links = []
        self._scripts = []
        self._scripts_head = []
        self._html_attrs: dict[str, str | Computed[str]] = {}
        self._callback_consumers: dict[str, CallbackConsumerNode] = {}

        with di_scope:
            super().__init__(_root_template, None, {"root": lambda: root_component(None)})

    @property
    def render(self):
        return self._render

    def _render(self):
        token = _active_di_scope.set(self._di_scope)
        app_token = _active_app_context.set(self._app) if self._app else None
        try:
            self._property["on_before_rendering"]()
            self._mount_node()
            if self._app and self._app._hydrate and not self.__hydrated:
                self.__hydrated = True
                for child in self._children:
                    child._hydrate_node()
            for child in self._children:
                child._render()
            self._property["on_after_rendering"]()
            if self._app:
                self._app._record_phase("run_done")
            if ENVIRONMENT == "pyscript":
                _dom = inject(DOM_PORT_KEY)
                html_el = _dom.query_selector("html")
                for key, value in self._html_attrs.items():
                    current = html_el.getAttribute(key) if html_el else None
                    expected = value.value if isinstance(value, Computed) else value
                    if current != expected and html_el:
                        html_el.setAttribute(key, expected)
                if self.__loading:
                    self.__loading = False
                    if self._app:
                        style_text = self.style
                        if style_text is not None and not _dom.get_element_by_id("webcompy-scoped-styles"):
                            style_el = _dom.create_element("style")
                            style_el.setAttribute("id", "webcompy-scoped-styles")
                            style_el.textContent = "*[hidden]{display: none;} " + style_text
                            head_el = _dom.query_selector("head")
                            if head_el:
                                head_el.appendChild(style_el)
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
                if app_token is not None:
                    _active_app_context.reset(app_token)
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
    def style(self):
        if self._app is not None:
            store = self._app._component_store
        else:
            from webcompy.di import inject
            from webcompy.di._keys import _COMPONENT_STORE_KEY

            store = inject(_COMPONENT_STORE_KEY)
        return " ".join(style for component in store.components.values() if (style := component.scoped_style))

    # HTML attribute controllers
    def set_html_attr(self, key: str, value: str | Computed[str]):
        if key in self._callback_consumers:
            consumer_destroy(self._callback_consumers[key])
            del self._callback_consumers[key]
        self._html_attrs[key] = value
        if isinstance(value, Computed) and ENVIRONMENT == "pyscript":
            consumer = value.on_after_updating(
                lambda v, k=key: el.setAttribute(k, v) if (el := inject(DOM_PORT_KEY).query_selector("html")) else None
            )
            self._callback_consumers[key] = consumer
        if ENVIRONMENT == "pyscript":
            _dom = inject(DOM_PORT_KEY)
            html_el = _dom.query_selector("html")
            if html_el:
                html_el.setAttribute(key, value.value if isinstance(value, Computed) else value)

    def remove_html_attr(self, key: str):
        if key in self._callback_consumers:
            consumer_destroy(self._callback_consumers[key])
            del self._callback_consumers[key]
        if key in self._html_attrs:
            del self._html_attrs[key]
        if ENVIRONMENT == "pyscript":
            _dom = inject(DOM_PORT_KEY)
            html_el = _dom.query_selector("html")
            if html_el:
                html_el.removeAttribute(key)

    @property
    def html_attrs(self) -> dict[str, str]:
        return {k: (v.value if isinstance(v, Computed) else v) for k, v in self._html_attrs.items()}

    def _set_title(self, title: str):
        if self._head_props is not None:
            self._head_props._app_title = title

    # Head controllers
    def set_title(self, title: str):
        self._set_title(title)

    def set_meta(self, key: str, attributes: dict[str, str]):
        self._set_meta(key, attributes)

    def append_link(self, attributes: dict[str, str]):
        self._links.append(attributes)

    def append_script(
        self,
        attributes: dict[str, str],
        script: str | None = None,
        in_head: bool = False,
    ):
        if not in_head:
            self._scripts.append((attributes, script))
        else:
            self._scripts_head.append((attributes, script))

    def set_head(self, head: Head):
        self._set_title(head.get("title", ""))
        for key, value in head.get("meta", {}).items():
            self._set_meta(key, value)
        self._links = head.get("link", [])
        self._scripts_head = head.get("script", [])

    def update_head(self, head: Head):
        if "title" in head:
            self.set_title(head["title"])
        for key, meta in head.get("meta", {}).items():
            self.set_meta(key, meta)
        for link in head.get("link", []):
            self.append_link(link)
        for attrs, script in head.get("script", []):
            self.append_script(attrs, script, True)

    @property
    def head(self) -> HeadSignal:
        assert self._head_props is not None
        return {
            "title": self._head_props.title,
            "meta": self._head_props.head_meta,
            "link": self._links,
            "script": self._scripts_head,
        }

    @property
    def scripts(self):
        return self._scripts
