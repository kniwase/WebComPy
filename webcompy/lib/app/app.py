from typing import (
    Any,
    Callable,
    Iterable,
    Optional,
    Type,
    Union,
    List)
from ..component import WebcompyComponent, register_webcomponent
from browser import html, document
from ..core import Style, ImportCss
from ..router import create_router_view, RoutesOption


def init_webcompy(
    components: Iterable[Type[WebcompyComponent]] = [],
    routes: Iterable[RoutesOption] = [],
    global_styles: Iterable[Union[Style, ImportCss]] = [],
    on_loaded: Optional[Callable[[], Any]] = None
) -> None:
    routes_frozen = tuple(routes)

    all_components: List[Type[WebcompyComponent]] = []
    all_components.extend(components)
    all_components.extend(r['component'] for r in routes_frozen)

    router_component = create_router_view(routes_frozen)
    all_components.append(router_component)

    styles = ['\n'.join(map(str, global_styles))]

    for component in all_components:
        scoped_css = '\n'.join(f'{component.tag_name} {style}'
                               for style in component.get_scoped_styles())
        if scoped_css:
            styles.append(scoped_css)

    document.head <= html.STYLE('\n'.join(styles))

    for component in all_components:
        register_webcomponent(component)

    if on_loaded is not None:
        on_loaded()
