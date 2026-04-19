from __future__ import annotations

import contextlib
from typing import TypedDict

from webcompy.components import ComponentGenerator, WebComPyComponentException
from webcompy.di._keys import _ROUTER_KEY
from webcompy.di._scope import _active_di_scope
from webcompy.elements.types import Element, SwitchElement
from webcompy.router._context import RouterContext
from webcompy.router._router import Router


class RouterPageRequired(TypedDict):
    path: str


class RouterPage(RouterPageRequired, total=False):
    component: ComponentGenerator[RouterContext]
    children: list[RouterPage]


class RouterView(Element):
    def __init__(self) -> None:
        scope = _active_di_scope.get(None)
        if scope is None:
            raise WebComPyComponentException("No DI scope available for RouterView.")
        router_instance: Router | None = None
        with contextlib.suppress(Exception):
            router_instance = scope.inject(_ROUTER_KEY)
        if router_instance is None:
            raise WebComPyComponentException("'Router' instance is not provided in DI scope.")

        super().__init__(
            tag_name="div",
            attrs={"webcompy-routerview": True},
            children=[SwitchElement(router_instance.__cases__, router_instance.__default__)],
        )
