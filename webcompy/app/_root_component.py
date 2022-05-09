from webcompy.elements import html
from webcompy.elements._dom_objs import DOMNode
from webcompy._browser._modules import browser
from webcompy.components._abstract import NonPropsComponentBase
from webcompy.components._component import Component
from webcompy.components._generator import ComponentGenerator, ComponentStore
from webcompy.components._decorators import component_template
from webcompy.router._router import Router
from webcompy.router._view import RouterView
from webcompy.router._link import TypedRouterLink
from webcompy.exception import WebComPyException


class AppRootComponent(NonPropsComponentBase):
    @component_template
    def template(self):
        return html.DIV({"id": "webcompy-app"}, self.context.slots("root"))


class AppDocumentRoot(Component):
    _router: Router | None
    __loading: bool

    def __init__(
        self, root_component: ComponentGenerator[None], router: Router | None
    ) -> None:
        self.__loading = True
        self._router = router
        if self._router:
            RouterView.__set_router__(self._router)
            TypedRouterLink.__set_router__(self._router)
        super().__init__(AppRootComponent, None, {"root": lambda: root_component(None)})

    @property
    def render(self):
        return self._render

    def _render(self):
        if browser and self.__loading:
            self.__loading = False
            browser.document.getElementById("webcompy-loading").remove()
        self._property["on_before_rendering"]()
        for child in self._children:
            child._render()
        self._property["on_after_rendering"]()

    def _init_node(self) -> DOMNode:
        if browser:
            node = browser.document.getElementById("webcompy-app")
            for name in tuple(node.attrs.keys()):
                if name != "id":
                    del node.attrs[name]
            node.__webcompy_node__ = True
            return node
        else:
            raise WebComPyException("Not in Browser environment.")

    def _mount_node(self):
        pass

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self) -> tuple["Component", ...]:
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
        return " ".join(
            style
            for component in ComponentStore.components.values()
            if (style := component.scoped_style)
        )

    def _render_html(
        self, newline: bool = False, indent: int = 2, count: int = 0
    ) -> str:
        hidden = self._attrs.get("hidden")
        self._attrs["hidden"] = True
        html = super()._render_html(newline, indent, count)
        if hidden is None:
            del self._attrs["hidden"]
        else:
            self._attrs["hidden"] = hidden
        return html
