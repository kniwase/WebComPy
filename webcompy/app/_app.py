from webcompy.components import ComponentGenerator
from webcompy.router import Router
from webcompy.app._root_component import AppDocumentRoot


class WebComPyApp:
    _root: AppDocumentRoot

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

    @property
    def set_title(self):
        return self._root.set_title

    @property
    def set_meta(self):
        return self._root.set_meta

    @property
    def append_link(self):
        return self._root.append_link

    @property
    def append_script(self):
        return self._root.append_script

    @property
    def set_head(self):
        return self._root.set_head

    @property
    def update_head(self):
        return self._root.update_head
