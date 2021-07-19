from typing import (Any, Optional, Type, Callable)
from browser import webcomponent
import re
from .utils import get_component_class_name
from .prop import get_observed_attributes, get_prop_callback
from ..core import pop_obj


def register_webcomponent(component: Type[Any], name: Optional[str] = None):
    class WebComponent:
        appendChild: Callable[[Any], None]
        shadow_root: Any

        def __init__(self) -> None:
            self.root = self
            self._webcompy_component = component(self, self.root)

        @property
        def is_webcompy_component(self) -> bool:
            return True

        def connectedCallback(self):
            self._webcompy_component.on_connected()
            self._webcompy_component.render()

        def disconnectedCallback(self):
            self._webcompy_component.on_disconnected()
            del self._webcompy_component

        def observedAttributes(self):
            component_name = get_component_class_name(component)
            observed_attributes = get_observed_attributes(component_name)
            return observed_attributes

        def attributeChangedCallback(
                self, prop_name: str, _: int, new: str, __: Any):
            component_name = get_component_class_name(component)
            prop_callback_name = get_prop_callback(
                component_name,
                prop_name[1:] if prop_name.startswith(':') else prop_name
            )
            if prop_callback_name:
                prop_callback = self._webcompy_component.__getattribute__(
                    prop_callback_name)
                if prop_callback:
                    value = pop_obj(new) if prop_name.startswith(':') else new
                    prop_callback(value)

    if not name:
        name = convert_camel_to_kebab(component)
    webcomponent.define(name, WebComponent)

    return name


pattern = re.compile(r'(?<!^)(?=[A-Z])')


def convert_camel_to_kebab(component: Type[Any]):
    class_name = get_component_class_name(component)
    name = pattern.sub('-', class_name).lower().strip('-')
    return name
