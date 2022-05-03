from webcompy.components import ComponentGenerator
from webcompy.router import Router
from webcompy.app._root_component import AppDocumentRoot


class WebComPyApp:
    _root: AppDocumentRoot
    _router: Router | None

    def __init__(
        self,
        *,
        root_component: ComponentGenerator[None],
        router: Router | None = None,
    ) -> None:
        self._root = AppDocumentRoot(root_component, router)

    @property
    def __routes__(self):
        return self._root.routes

    @property
    def __router_mode__(self):
        return self._root.router_mode

    @property
    def __render__(self):
        return self._root.__render__

    @property
    def __component_styles__(self):
        return self._root.style
