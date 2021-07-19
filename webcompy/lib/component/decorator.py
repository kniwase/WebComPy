from typing import Any, Type, List
from .base import WebcompyComponentBase
from ..core import Style


def define_component(template: str,
                     styles: List[Style] = [],
                     use_shadow_dom: bool = False):
    def deco(cls: Type[WebcompyComponentBase]):
        class WebcompyComponent(cls):
            cls._scoped_styles = styles
            _use_shadow_dom = use_shadow_dom

            def __init__(self, conponent: Any, root: Any) -> None:
                super().__init__()
                self._set_template(template)
                self._refs = {}
                self._conponent = conponent
                self._root = root
        return WebcompyComponent
    return deco
