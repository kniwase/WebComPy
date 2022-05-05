from functools import partial
from re import compile as re_compile, escape as re_escape
import urllib.parse
from typing import (
    Any,
    Callable,
    ClassVar,
    List,
    Literal,
    Match,
    Sequence,
    Tuple,
    TypeAlias,
    Union,
)
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.components import ComponentGenerator, WebComPyComponentException
from webcompy.elements.types._switch import NodeGenerator
from webcompy.reactive._computed import computed_property
from webcompy.router._change_event_hander import Location
from webcompy.router._pages import RouterPage
from webcompy.router._context import TypedRouterContext, RouterContext


RouteType: TypeAlias = Tuple[
    str,
    Callable[[str], Match[str] | None],
    List[str],
    ComponentGenerator[RouterContext],
    RouterPage,
]

_convert_to_regex_pattern = partial(re_compile(r"\\\{[^\{\}/]+\\\}").sub, r"([^/]*?)")
_get_path_params = re_compile(r"{([^\{\}/]+)}").findall


class Router:
    _instance: ClassVar[Union["Router", None]] = None

    _location: Location
    __mode__: Literal["hash", "history"]
    __routes__: list[RouteType]

    def __init__(
        self,
        *pages: RouterPage,
        default: ComponentGenerator[TypedRouterContext[Any, Any, Any]] | None = None,
        mode: Literal["hash", "history"] = "hash",
        base_url: str = "",
    ) -> None:
        if Router._instance:
            raise WebComPyComponentException("Only one instance of 'Router' can exist.")
        else:
            Router._instance = self
        self.__mode__ = mode
        self.__base_url__ = base_url.strip().strip("/")
        self._base_url_stripper = partial(
            re_compile("^" + re_escape("/" + self.__base_url__)).sub, ""
        )
        self._location = Location(self.__mode__, self.__base_url__)
        self.__routes__ = self._generate_routes(pages)
        self._default = default

    @computed_property
    def __cases__(self):
        return list(map(self._get_elements_generator, self.__routes__))

    def __default__(self) -> ElementChildren:
        if self._default:
            current_path, search = self._get_current_path()
            if current_path == "//:404://":
                current_path = "/404.html"
            elif self.__mode__ == "history" and self.__base_url__:
                current_path = self._base_url_stripper(current_path)
            props = self._generate_router_context(
                current_path,
                search,
                None,
                [],
            )
            return self._default(props)
        else:
            return "Not Found"

    def _get_current_path(self):
        decoded_href = tuple(
            map(urllib.parse.unquote, self._location.value.split("?", 2))
        )
        pathname, search = (
            (decoded_href[0], "") if len(decoded_href) == 1 else decoded_href
        )
        return pathname, search

    def _get_elements_generator(self, args: RouteType) -> Tuple[Any, NodeGenerator]:
        match_targeted_routes, path_param_names, component = args[1:-1]
        current_path, search = self._get_current_path()
        if self.__mode__ == "history" and self.__base_url__:
            current_path = self._base_url_stripper(current_path)
        match = match_targeted_routes(current_path.strip("/"))
        if match:
            props = self._generate_router_context(
                current_path,
                search,
                match,
                path_param_names,
            )
            return (match, lambda: component(props))
        else:
            return (match, lambda: None)

    def _generate_router_context(
        self,
        pathname: str,
        search: str,
        match: Match[str] | None,
        path_param_names: List[str],
    ):
        query = (
            {
                name: value
                for name, value in (
                    [it[0], ""] if len(it) == 1 else it
                    for it in (q.split("=", 2) for q in search.split("&"))
                )
                if name and value
            }
            if search
            else {}
        )
        if match:
            path_params = (
                dict(zip(path_param_names, match.groups())) if path_param_names else {}
            )
        else:
            path_params = {}
        return TypedRouterContext.__create_instance__(
            path=pathname,
            query_params=query,
            path_params=path_params,
            state=self._location.state if self._location.state else {},
        )

    def _generate_route_matcher(self, path: str):
        return re_compile(_convert_to_regex_pattern(re_escape(path)) + "$").match

    def _generate_routes(self, pages: Sequence[RouterPage]) -> list[RouteType]:
        return [
            (*path, component, page)
            for path, component, page in zip(
                map(
                    lambda path: (
                        path,
                        self._generate_route_matcher(path),
                        _get_path_params(path),
                    ),
                    map(lambda page: page["path"].strip("/"), pages),
                ),
                map(lambda page: page["component"], pages),
                pages,
            )
        ]

    def __set_path__(self, path: str, state: dict[str, Any] | None):
        self._location.__set_path__(path, state)
