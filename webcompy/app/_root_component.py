from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict
from uuid import uuid4

from webcompy._browser._modules import browser
from webcompy.components._component import Component, HeadPropsStore, _active_app_context
from webcompy.components._generator import (
    ComponentGenerator,
    define_component,
)
from webcompy.di._keys import _HEAD_PROPS_KEY, _ROUTER_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.elements._dom_objs import DOMNode
from webcompy.exception import WebComPyException
from webcompy.router._keys import RouterKey
from webcompy.router._router import Router
from webcompy.signal import Computed

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


def _app_root_setup(context):
    return html.DIV({"id": "webcompy-app"}, context.slots("root"))


_app_root_setup.__webcompy_component_definition__ = True


@define_component
def AppRootComponent(context):
    return html.DIV({"id": "webcompy-app"}, context.slots("root"))


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
        self._instance_id = uuid4()
        self.__loading = True
        self.__hydrated = False
        self._router = router
        self._di_scope = di_scope
        self._selector = selector
        self._app = app

        head_props = HeadPropsStore()
        self._head_props = head_props
        di_scope.provide(_HEAD_PROPS_KEY, head_props)
        if self._router:
            di_scope.provide(_ROUTER_KEY, self._router)
            di_scope.provide(RouterKey, self._router)
        if browser:

            def updte_title(title: str | None):
                if title is not None:
                    browser.document.title = title  # type: ignore

            head_props.title.on_after_updating(updte_title)

        self._set_title("")
        self._links = []
        self._scripts = []
        self._scripts_head = []

        with di_scope:
            super().__init__(_app_root_setup, None, {"root": lambda: root_component(None)})

    @property
    def render(self):
        return self._render

    def _render(self):
        token = _active_di_scope.set(self._di_scope)
        app_token = _active_app_context.set(self._app) if self._app else None
        try:
            self._property["on_before_rendering"]()
            if self._app and self._app._hydrate and not self.__hydrated:
                self.__hydrated = True
                for child in self._children:
                    child._hydrate_node()
            for child in self._children:
                child._render()
            self._property["on_after_rendering"]()
            if self._app:
                self._app._record_phase("run_done")
            if browser and self.__loading:
                self.__loading = False
                selector = self._selector or "#webcompy-app"
                loading_el = browser.document.querySelector(
                    f"{selector} > #webcompy-loading"
                ) or browser.document.getElementById("webcompy-loading")
                if loading_el:
                    loading_el.remove()
                if self._app:
                    self._app._record_phase("loading_removed")
                    self._app._emit_profile_summary()
        finally:
            if not browser:
                if app_token is not None:
                    _active_app_context.reset(app_token)
                _active_di_scope.reset(token)

    def _init_node(self) -> DOMNode:
        if browser:
            selector = self._selector or "#webcompy-app"
            node = browser.document.querySelector(selector)
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
            raise WebComPyException("Not in Browser environment.")

    def _mark_as_prerendered(self, node: DOMNode):
        node.__webcompy_prerendered_node__ = True
        for child in getattr(node, "childNodes", []):
            self._mark_as_prerendered(child)

    def _mount_node(self):
        pass

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
