from typing import (
    Any,
    Callable,
    Iterable,
    Optional,
    Type,
    Union)
from ..component import WebcompyComponent, register_webcomponent
from browser import html, document
from ..core import Style, ImportCss
from ..elements import create_router_view, RoutesOption


def init_webcompy(
    components: Iterable[Type[WebcompyComponent]] = [],
    routes: Iterable[RoutesOption] = [],
    global_styles: Iterable[Union[Style, ImportCss]] = [],
    on_loaded: Optional[Callable[[], Any]] = None
) -> None:
    router_component = create_router_view(routes)
    all_components = list(components)
    all_components.append(router_component)

    styles = ['\n'.join(map(str, global_styles))]

    for component in all_components:
        scoped_css = '\n'.join(f'{component.get_tag_name()} {style}'
                               for style in component.get_scoped_styles())
        if scoped_css:
            styles.append(scoped_css)

    document.head <= html.STYLE('\n'.join(styles))

    for component in all_components:
        register_webcomponent(component)

    if on_loaded is not None:
        on_loaded()
