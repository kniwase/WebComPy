from typing import Iterable, Any, Type, TypedDict, cast
from browser import window
from ..component import (
    WebcompyComponentBase,
    WebcompyComponent,
    define_component
)


class RoutesOption(TypedDict):
    path: str
    component: Type[WebcompyComponent]


def create_router_view(
        routes: Iterable[RoutesOption]
) -> Type[WebcompyComponent]:
    @define_component('')
    class RouterView(WebcompyComponentBase):
        prop: dict[str, str] = {'path': ''}

        def __init__(self) -> None:
            self.routes = self.map_routes(routes)
            self._set_template(self.generate_template())
            window.onhashchange = self.onhashchange

        def map_routes(self, routes: Iterable[RoutesOption]):
            return {r['path']: r['component'].tag_name
                    for r in routes}

        def on_connected(self) -> None:
            self._set_template(self.generate_template())

        def onhashchange(self, _: Any):
            self._set_template(self.generate_template())

        def generate_template(self):
            uri = window.location.hash[1:]
            self.prop['path'] = uri
            if uri in self.routes:
                return '<{tag} :route="prop" />'.format(tag=self.routes[uri])
            elif '*' in self.routes:
                return '<{tag} :route="prop" />'.format(tag=self.routes['*'])
            else:
                return "<div><span>Not Found</span></div>"

    return cast(Type[WebcompyComponent], RouterView)
