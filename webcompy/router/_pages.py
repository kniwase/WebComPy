from typing import Any, TypedDict

from webcompy.components import ComponentGenerator, WebComPyComponentException
from webcompy.router._context import TypedRouterContext


class WebComPyRouterException(WebComPyComponentException):
    pass


class RouterPageRequired(TypedDict):
    component: ComponentGenerator[TypedRouterContext[Any, Any, Any]]
    path: str


class RouterPage(RouterPageRequired, total=False):
    path_params: list[dict[str, str]]
    meta: Any
