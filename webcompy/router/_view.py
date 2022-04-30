from typing import ClassVar, List, TypedDict, Union
from webcompy.elements.types import Element, SwitchElement
from webcompy.components import ComponentGenerator, WebComPyComponentException
from webcompy.router._router import Router
from webcompy.router._context import RouterContext


class RouterPageRequired(TypedDict):
    path: str


class RouterPage(RouterPageRequired, total=False):
    component: ComponentGenerator[RouterContext]
    children: List["RouterPage"]


class RouterView(Element):
    _instance: ClassVar[Union["RouterView", None]] = None
    _router: ClassVar[Union[Router, None]] = None

    def __init__(self) -> None:
        if RouterView._instance:
            raise WebComPyComponentException(
                "Only one instance of 'RouterView' can exist."
            )
        else:
            RouterView._instance = self
        if RouterView._router is None:
            raise WebComPyComponentException("'Router' instance is not declarated.")

        super().__init__(
            tag_name="div",
            attrs={"webcompy-routerview": True},
            children=[
                SwitchElement(
                    RouterView._router.__cases__, RouterView._router.__default__
                )
            ],
        )

    @staticmethod
    def __set_router__(router: Router | None):
        RouterView._router = router
