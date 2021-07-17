from typing import Iterable, Any, Type, TypedDict
from browser import window
from ..component import (
    WebcompyComponentBase,
    WebcompyComponent,
    define_component,
    get_component_tag_name
)


class RoutesOption(TypedDict):
    path: str
    component: Type[WebcompyComponent]


def create_router_view(routes: Iterable[RoutesOption]):
    @define_component('')
    class RouterView(WebcompyComponentBase):
        prop: dict[str, str] = {'path': ''}

        def __init__(self) -> None:
            self.routes = self.map_routes(routes)
            self._template = self.generate_template()
            window.onhashchange = self.onhashchange

        def map_routes(self, routes: Iterable[RoutesOption]):
            return {r['path']: get_component_tag_name(r['component'])
                    for r in routes}

        def onhashchange(self, _: Any):
            self._template = self.generate_template()
            self.init_vdom()
            self.render()

        def generate_template(self):
            uri = window.location.hash[1:]
            self.prop['path'] = uri
            if uri in self.routes:
                return '<{tag} :route="prop" />'.format(tag=self.routes[uri])
            elif '*' in self.routes:
                return '<{tag} :route="prop" />'.format(tag=self.routes['*'])
            else:
                return "<div></div>"

    return RouterView
