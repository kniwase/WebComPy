from typing import Any, Dict, List, TypedDict
from webcompy.components import ComponentGenerator
from webcompy.router._context import TypedRouterContext
from webcompy.components import WebComPyComponentException


class WebComPyRouterException(WebComPyComponentException):
    pass


class RouterPageRequired(TypedDict):
    component: ComponentGenerator[TypedRouterContext[Any, Any, Any]]
    path: str


class RouterPage(RouterPageRequired, total=False):
    path_params: List[Dict[str, str]]
    meta: Any
