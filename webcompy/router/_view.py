from __future__ import annotations

from webcompy._browser._modules import browser
from webcompy.di import inject
from webcompy.di._exceptions import InjectionError
from webcompy.di._keys import _ROUTER_KEY
from webcompy.elements.types._dynamic import DynamicElement
from webcompy.elements.types._switch import SwitchElement


class RouterView(DynamicElement):
    def __init__(self) -> None:
        try:
            router = inject(_ROUTER_KEY)
        except InjectionError:
            raise RuntimeError("'Router' instance is not provided via DI.") from None
        self._router = router
        self._switch = SwitchElement(router.__cases__, router.__default__)
        super().__init__()

    def _on_set_parent(self):
        self._children = [self._switch]
        self._switch._parent = self
        self._re_index_children()
        if not browser:
            self._switch._on_set_parent()
            if self._router._preload:
                self._router.preload_lazy_routes()
