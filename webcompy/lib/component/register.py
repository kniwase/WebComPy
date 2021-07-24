from typing import (Any, Dict, Type, Callable)
from browser import webcomponent
from .base import WebcompyComponent
from .prop import get_observed_attributes, get_prop_callback
from ..core import pop_obj


def init_component(
    component: WebcompyComponent,
    web_conponent: Any,
    root: Any,
    props: Dict[str, Any]
):
    component.__init_component__(web_conponent, root, props)


def render(component: WebcompyComponent):
    component.__render__()


def register_webcomponent(component: Type[WebcompyComponent]):
    class WebComponent:
        attrs: Dict[str, Any]
        isInitialzed: bool
        isConnected: bool
        attachShadow: Callable[[Dict[str, Any]], Any]
        appendChild: Callable[[Any], None]
        webcompy_component: WebcompyComponent
        root: Any

        def __init__(self) -> None:
            self.isInitialzed = False
            self.webcompy_component = component()
            if component.get_shadow_dom_mode():
                self.root = self.attachShadow({'mode': 'open'})
            else:
                self.root = self

        def connectedCallback(self):
            attributes = dict(sorted(self.attrs.items(), key=lambda x: x[0]))
            observed_attributes = set(self.observedAttributes())
            props = dict(
                (name[1:] if name.startswith(':') else name,
                 pop_obj(value) if name.startswith(':') else value)
                for name, value in attributes.items()
                if name in observed_attributes
            )
            attrs_to_delete = (
                name
                for name in attributes.keys()
                if name in observed_attributes
            )
            for name in attrs_to_delete:
                del self.attrs[name]

            init_component(self.webcompy_component, self, self.root, props)
            self.webcompy_component.on_connected()
            render(self.webcompy_component)
            self.isInitialzed = True

        def disconnectedCallback(self):
            self.webcompy_component.on_disconnected()
            del self.webcompy_component

        def observedAttributes(self):
            return get_observed_attributes(component.get_tag_name())

        def attributeChangedCallback(
                self, prop_name: str, _: int, new: str, __: Any):
            if self.isConnected and self.isInitialzed:
                prop_callback: Callable[[Any], None] = getattr(
                    self.webcompy_component,
                    get_prop_callback(component.get_tag_name(), prop_name)
                )
                if not prop_name.startswith(':'):
                    prop_callback(new)
                elif prop_name in self.attrs:
                    prop_callback(pop_obj(new))
                    del self.attrs[prop_name]

    webcomponent.define(component.get_tag_name(), WebComponent)
