from typing import (Any, Dict, Type, Callable)
from browser import webcomponent
from .base import WebcompyComponent
from .prop import get_observed_attributes, get_prop_callback
from ..core import pop_obj


def register_webcomponent(component: Type[WebcompyComponent]):
    class WebComponent:
        attrs: Dict[str, Any]
        attachShadow: Callable[[Dict[str, Any]], Any]
        appendChild: Callable[[Any], None]
        root: Any

        def __init__(self) -> None:
            if component.get_shadow_dom_mode():
                self.root = self.attachShadow({'mode': 'open'})
            else:
                self.root = self
            self._webcompy_component = component(self, self.root)
            self._render = self._webcompy_component.get_render()

        @property
        def is_webcompy_component(self) -> bool:
            return True

        def connectedCallback(self):
            self._webcompy_component.on_connected()
            self._render()

        def disconnectedCallback(self):
            self._webcompy_component.on_disconnected()
            del self._webcompy_component

        def observedAttributes(self):
            return get_observed_attributes(component.get_tag_name())

        def attributeChangedCallback(
                self, prop_name: str, _: int, new: str, __: Any):
            prop_callback: Callable[[Any], None] = getattr(
                self._webcompy_component,
                get_prop_callback(component.get_tag_name(), prop_name)
            )
            if not prop_name.startswith(':'):
                prop_callback(new)
            elif prop_name in self.attrs:
                prop_callback(pop_obj(new))
                del self.attrs[prop_name]

    webcomponent.define(component.get_tag_name(), WebComponent)
