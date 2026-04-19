from __future__ import annotations

from typing import TypedDict
from uuid import uuid4

from webcompy._browser._modules import browser
from webcompy.components._component import Component, HeadPropsStore
from webcompy.components._generator import ComponentGenerator, ComponentStore, define_component
from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY, _ROUTER_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.elements._dom_objs import DOMNode
from webcompy.exception import WebComPyException
from webcompy.router._router import Router
from webcompy.signal import Computed


class Head(TypedDict, total=False):
    title: str
    meta: dict[str, dict[str, str]]
    link: list[dict[str, str]]
    script: list[tuple[dict[str, str], str | None]]


class HeadSignal(TypedDict):
    title: Computed[str]
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
    _di_scope: DIScope
    _links: list[dict[str, str]]
    _scripts: list[tuple[dict[str, str], str | None]]
    _scripts_head: list[tuple[dict[str, str], str | None]]
    __loading: bool

    def __init__(
        self,
        root_component: ComponentGenerator[None],
        router: Router | None,
        di_scope: DIScope,
    ) -> None:
        self._instance_id = uuid4()
        self.__loading = True
        self._router = router
        self._di_scope = di_scope
        self.__head_props = HeadPropsStore()
        self._set_title("")
        self._links = []
        self._scripts = []
        self._scripts_head = []

        di_scope.provide(_HEAD_PROPS_KEY, self.__head_props)
        di_scope.provide(_COMPONENT_STORE_KEY, ComponentStore)
        if router is not None:
            di_scope.provide(_ROUTER_KEY, router)
        if browser:

            def updte_title(title: str):
                browser.document.title = title  # type: ignore

            self.__head_props.title.on_after_updating(updte_title)

        super().__init__(_app_root_setup, None, {"root": lambda: root_component(None)})

    @property
    def render(self):
        return self._render

    def _render(self):
        di_token = _active_di_scope.set(self._di_scope)
        try:
            self._property["on_before_rendering"]()
            for child in self._children:
                child._render()
            self._property["on_after_rendering"]()
            if browser and self.__loading:
                self.__loading = False
                browser.document.getElementById("webcompy-loading").remove()
        finally:
            _active_di_scope.reset(di_token)

    def _init_node(self) -> DOMNode:
        if browser:
            node = browser.document.getElementById("webcompy-app")
            for name in tuple(node.getAttributeNames()):
                if name != "id":
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
        from webcompy.di._exceptions import InjectionError
        from webcompy.di._keys import _COMPONENT_STORE_KEY

        try:
            store = self._di_scope.inject(_COMPONENT_STORE_KEY)
        except InjectionError:
            from webcompy.components._generator import _get_default_component_store

            store = _get_default_component_store()
        return " ".join(style for component in store.components.values() if (style := component.scoped_style))

    def _render_html(self, newline: bool = False, indent: int = 2, count: int = 0) -> str:
        hidden = self._attrs.get("hidden")
        self._attrs["hidden"] = True
        html = super()._render_html(newline, indent, count)
        if hidden is None:
            del self._attrs["hidden"]
        else:
            self._attrs["hidden"] = hidden
        return html

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
        return {
            "title": self.__head_props.title,
            "meta": self.__head_props.head_meta,
            "link": self._links,
            "script": self._scripts_head,
        }

    @property
    def scripts(self):
        return self._scripts
