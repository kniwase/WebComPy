from __future__ import annotations

from webcompy.di import inject
from webcompy.di._exceptions import InjectionError
from webcompy.di._keys import _ROUTER_KEY
from webcompy.elements.types._dynamic import DynamicElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.signal._base import SignalBase


class _RouterSwitchElement(SwitchElement):
    def _on_set_parent(self):
        if not self._signal_activated:
            self._signal_activated = True
            if isinstance(self._cases, SignalBase):
                self._add_callback_node(self._cases.on_after_updating(self._refresh_sync))
            else:
                for cond, _ in self._cases:
                    if isinstance(cond, SignalBase):
                        self._add_callback_node(cond.on_after_updating(self._refresh_sync))


class RouterView(DynamicElement):
    def __init__(self) -> None:
        try:
            router = inject(_ROUTER_KEY)
        except InjectionError:
            raise RuntimeError("'Router' instance is not provided via DI.") from None
        self._router = router
        self._switch = _RouterSwitchElement(router.__cases__, router.__default__)
        super().__init__()

    def _on_set_parent(self):
        self._children = [self._switch]
        self._switch._parent = self
        self._re_index_children()
        if self._router._preload:
            self._router.preload_lazy_routes()
