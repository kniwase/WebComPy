from typing import Any, Type, List
from .base import WebcompyComponentBase
from ..core import Style


def define_component(template: str, styles: List[Style] = []):
    def deco(cls: Type[WebcompyComponentBase]):
        class WebcompyComponent(cls):
            cls._scoped_styles = styles

            def __init__(self, conponent: Any) -> None:
                self._conponent = conponent
                super().__init__()
        return WebcompyComponent
    return deco
