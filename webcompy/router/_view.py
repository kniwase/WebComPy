from __future__ import annotations

from typing import TypedDict

from webcompy.components import ComponentGenerator
from webcompy.di import inject
from webcompy.di._exceptions import InjectionError
from webcompy.di._keys import _ROUTER_KEY
from webcompy.elements.types import Element, SwitchElement
from webcompy.router._context import RouterContext


class RouterPageRequired(TypedDict):
    path: str


class RouterPage(RouterPageRequired, total=False):
    component: ComponentGenerator[RouterContext]
    children: list[RouterPage]


class RouterView(Element):
    def __init__(self) -> None:
        try:
            router = inject(_ROUTER_KEY)
        except InjectionError:
            raise RuntimeError("'Router' instance is not provided via DI.") from None

        super().__init__(
            tag_name="div",
            attrs={"webcompy-routerview": True},
            children=[SwitchElement(router.__cases__, router.__default__)],
        )
