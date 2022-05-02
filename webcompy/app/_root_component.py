from webcompy.elements import html
from webcompy.brython import DOMNode, browser
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
    routes: list[str]
    _router: Router | None

    def __init__(
        self, root_component: ComponentGenerator[None], router: Router | None
    ) -> None:
        self._router = router
        if self._router:
            RouterView.__set_router__(self._router)
            TypedRouterLink.__set_router__(self._router)
        super().__init__(AppRootComponent, None, {"root": lambda: root_component(None)})
        self.routes = [p[0] for p in self._router.__routes__] if self._router else []
        self.router_mode = self._router.__mode__ if self._router else None

    def render(self):
        if browser:
            style_node = browser.document.createElement("style")
            style_node.textContent = self._style
            browser.document.body.appendChild(style_node)
            self._render()

    def _render(self):
        self._mount_node()
        self._property["on_before_rendering"]()
        for child in self._children:
            child._render()
        self._property["on_after_rendering"]()

    def _init_node(self) -> DOMNode:
        if browser:
            node = browser.document.createElement("div")
            node.setAttribute("id", "webcompy-app")
            node.__webcompy_node__ = True
            return node
        else:
            raise WebComPyException("Not in Browser environment.")

    def _mount_node(self):
        if browser:
            old_node = browser.document.getElementById("webcompy-app")
            old_node.parent.replaceChild(self._get_node(), old_node)

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self) -> tuple["Component", ...]:
        return (self,)

    @property
    def _style(self):
        return "\n".join(
            style
            for component in ComponentStore.components.values()
            if (style := component.scoped_style)
        )

    def render_html(self, path: str | None = None, indent: int = 2):
        if self._router and path is not None:
            self._router.__set_path__(path, None)
        return self._render_html(0, indent)
