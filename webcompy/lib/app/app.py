from typing import Iterable, Optional, Type, Union, TypedDict, List, Tuple
from ..component import WebcompyComponent, register_webcomponent
from browser import html, document
from ..core import Style, ImportCss
from ..router import create_router_view, RoutesOption


class ComponentsOption(TypedDict):
    name: str
    component: Type[WebcompyComponent]


def init_webcompy(
    components: Iterable[Union[Type[WebcompyComponent], ComponentsOption]] = [],
    routes: Iterable[RoutesOption] = [],
    global_styles: Iterable[Union[Style, ImportCss]] = [],
    on_loaded: Optional[Callable[[], Any]] = None
) -> None:
    routes_frozen = tuple(routes)

    component_name_pair = get_component_name_pair(routes_frozen, components)
    component_name_pair.append((create_router_view(routes_frozen),
                                'router-view'))

    styles = ['\n'.join(map(str, global_styles))]

    for component, name in component_name_pair:
        element_name = register_webcomponent(component, name)
        scoped_css = '\n'.join(f'{element_name} {style}'
                               for style in component.scoped_styles)
        if scoped_css:
            styles.append(scoped_css)

    document.head <= html.STYLE('\n'.join(styles))

    if on_loaded is not None:
        on_loaded()


def get_component_name_pair(
        routes: Tuple[RoutesOption, ...],
        components: Iterable[Union[Type[WebcompyComponent], ComponentsOption]]):
    ret: List[Tuple[Type[WebcompyComponent], Optional[str]]] = []

    for r in routes:
        ret.append((r['component'], None))

    for option in components:
        if isinstance(option, dict):
            name = option['name']
            component = option['component']
        else:
            name = None
            component = option
        ret.append((component, name))
    return ret
