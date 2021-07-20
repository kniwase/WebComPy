from typing import Any, Optional, Type, List, cast
from .base import WebcompyComponentBase, WebcompyComponent
from .utils import convert_camel_to_kebab
from ..core import Style


def define_component(template: str,
                     styles: List[Style] = [],
                     tag_name: Optional[str] = None,
                     use_shadow_dom: bool = False):
    def deco(cls: Type[WebcompyComponentBase]) -> Type[WebcompyComponent]:
        class Component(cls):
            cls._scoped_styles = styles
            _use_shadow_dom = use_shadow_dom
            tag_name = tag_name if tag_name else convert_camel_to_kebab(
                cls.__name__)

            def __init__(self, conponent: Any, root: Any) -> None:
                super().__init__()
                self._component_vars = {
                    name: getattr(self, name)
                    for name in dir(self)
                    if not (name in set(dir(WebcompyComponentBase)) or name.startswith('_'))
                }
                self._set_template(template)
                self._refs = {}
                self._conponent = conponent
                self._root = root
        return cast(Type[WebcompyComponent], Component)
    return deco
