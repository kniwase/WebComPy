from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterView

from .navigation import SiteNavigation


@define_component("app-root")
def AppRoot(_: ComponentContext[None]):
    return html.DIV(
        {},
        SiteNavigation(None),
        RouterView(),
    )
