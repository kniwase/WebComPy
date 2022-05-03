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
    def __component__(self):
        return self._root
