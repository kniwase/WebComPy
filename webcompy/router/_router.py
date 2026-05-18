from __future__ import annotations

import urllib.parse
from collections.abc import Callable, Sequence
from contextlib import suppress
from functools import partial
from re import Match
from re import compile as re_compile
from re import escape as re_escape
from typing import (
    Any,
    Literal,
    TypeAlias,
)

from webcompy.components import ComponentGenerator
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._switch import NodeGenerator
from webcompy.ports._history import HistoryPort
from webcompy.router._context import RouterContext, TypedRouterContext
from webcompy.router._pages import RouterPage
from webcompy.signal._computed import computed_property

RouteType: TypeAlias = tuple[
    str,
    Callable[[str], Match[str] | None],
    list[str],
    ComponentGenerator[RouterContext],
    RouterPage,
]

_convert_to_regex_pattern = partial(re_compile(r"\\\{[^\{\}/]+\\\}").sub, r"([^/]*?)")
_get_path_params = re_compile(r"{([^\{\}/]+)}").findall


class Router:
    _history: HistoryPort | None
    __mode__: Literal["hash", "history"]
    __routes__: list[RouteType]

    def __init__(
        self,
        *pages: RouterPage,
        default: ComponentGenerator[TypedRouterContext[Any, Any, Any]] | None = None,
        history: HistoryPort | None = None,
        mode: Literal["hash", "history"] = "hash",
        base_url: str = "",
        preload: bool = True,
    ) -> None:
        self._history = history
        self.__mode__ = mode if history is None else history.mode
        self.__base_url__ = base_url.strip().strip("/")
        self._base_url_stripper = partial(re_compile("^" + re_escape("/" + self.__base_url__)).sub, "")
        self.__routes__ = self._generate_routes(pages)
        self._default = default
        self._preload = preload
        self.before_route_change: list[Callable[[str, str], bool | None]] = []
        self.after_route_change: list[Callable[[str], None]] = []
        self.on_route_error: list[Callable[[Exception], bool | None]] = []

    def _resolve_history(self) -> HistoryPort:
        history = self._history
        if history is None:
            from webcompy.di import inject
            from webcompy.ports._keys import HISTORY_PORT_KEY

            history = inject(HISTORY_PORT_KEY)
            self._history = history
            self.__mode__ = history.mode
        return history  # type: ignore[return-value]

    @computed_property
    def __cases__(self):
        try:
            return list(map(self._get_elements_generator, self.__routes__))
        except Exception as e:
            for handler in self.on_route_error:
                if handler(e) is True:
                    return []
            raise

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
        history = self._resolve_history()
        decoded_href = tuple(map(urllib.parse.unquote, history.value.split("?", 2)))
        pathname, search = (decoded_href[0], "") if len(decoded_href) == 1 else decoded_href
        return pathname, search

    def _get_elements_generator(self, args: RouteType) -> tuple[Any, NodeGenerator]:
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
        path_param_names: list[str],
    ):
        history = self._resolve_history()
        query = (
            {
                name: value
                for name, value in (
                    [it[0], ""] if len(it) == 1 else it for it in (q.split("=", 2) for q in search.split("&"))
                )
                if name and value
            }
            if search
            else {}
        )
        path_params = (
            (dict(zip(path_param_names, match.groups(), strict=True)) if path_param_names else {}) if match else {}
        )
        return TypedRouterContext.__create_instance__(
            path=pathname,
            query_params=query,
            path_params=path_params,
            state=history.state or {},
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
                strict=True,
            )
        ]

    def __set_path__(self, path: str, state: dict[str, Any] | None):
        history = self._resolve_history()
        for guard in self.before_route_change:
            if guard(history.value, path) is False:
                return
        history.navigate(path, state)
        for callback in self.after_route_change:
            callback(path)

    def preload_lazy_routes(self) -> None:
        if not self._preload:
            return
        from webcompy.di import inject
        from webcompy.ports._keys import HOST_PORT_KEY
        from webcompy.router._lazy import LazyComponentGenerator
        from webcompy.utils._environment import ENVIRONMENT

        lazy_components = [
            route[3]
            for route in self.__routes__
            if isinstance(route[3], LazyComponentGenerator)
            and route[3]._resolved is None
            and not route[3]._resolve_error
        ]
        if lazy_components:
            if ENVIRONMENT == "pyscript":

                def _batch_preload(components=lazy_components):
                    for c in components:
                        with suppress(Exception):
                            c._preload()

                inject(HOST_PORT_KEY).schedule_macro_task(_batch_preload)
            else:
                for c in lazy_components:
                    with suppress(Exception):
                        c._preload()

    def _get_component_for_path(self, path: str) -> ComponentGenerator[RouterContext] | None:
        clean_path = path
        if self.__mode__ == "history" and self.__base_url__:
            clean_path = self._base_url_stripper(clean_path)
        clean_path = clean_path.strip("/")
        for route in self.__routes__:
            _, matcher, _, component, _ = route
            if matcher(clean_path):
                return component
        return None
