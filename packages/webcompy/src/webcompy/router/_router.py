from __future__ import annotations

import urllib.parse
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
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
from webcompy.ports._history import HistoryPort
from webcompy.router._context import RouterContext, TypedRouterContext
from webcompy.router._pages import RouterPage
from webcompy.signal import computed_property

RouteType: TypeAlias = tuple[
    str,
    Callable[[str], Match[str] | None],
    list[str],
    ComponentGenerator[RouterContext],
    RouterPage,
]


@dataclass(frozen=True)
class RouteNode:
    segment: str
    component: ComponentGenerator[RouterContext]
    page: RouterPage


@dataclass(frozen=True)
class ChainEntry:
    full_path: str
    chain: tuple[RouteNode, ...]
    per_level_param_names: tuple[list[str], ...]


@dataclass(frozen=True)
class RouteMatch:
    path: str
    chain: tuple[RouteNode, ...]
    per_level_params: tuple[dict[str, str], ...]
    path_params: dict[str, str]
    query: dict[str, str]
    state: dict[str, Any]


_convert_to_regex_pattern = partial(re_compile(r"\\\{[^\{\}/]+\\\}").sub, r"([^/]*?)")
_get_path_params = re_compile(r"{([^\{\}/]+)}").findall


class Router:
    _history: HistoryPort | None
    __mode__: Literal["hash", "history"]
    __routes__: list[RouteType]
    __chains__: list[ChainEntry]
    __pages__: tuple[RouterPage, ...]

    def __init__(
        self,
        *pages: RouterPage,
        default: ComponentGenerator[TypedRouterContext[Any, Any, Any]] | None = None,
        history: HistoryPort | None = None,
        mode: Literal["hash", "history"] = "hash",
        base_url: str = "",
        preload: bool = True,
    ) -> None:
        self.__pages__ = pages
        self._history = history
        self.__mode__ = mode if history is None else history.mode
        if history is not None:
            history.set_navigation_callback(self.__set_path__)
        self.__base_url__ = base_url.strip().strip("/")
        self._base_url_stripper = partial(re_compile("^" + re_escape("/" + self.__base_url__)).sub, "")
        self.__routes__, self.__chains__ = self._generate_routes(pages)
        self._default = default
        self._preload = preload
        self.before_route_change: list[Callable[[str, str], bool | None]] = []
        self.after_route_change: list[Callable[[str], None]] = []
        self.on_route_error: list[Callable[[Exception], bool | None]] = []

    def _clone_for_request(self) -> Router:
        return Router(
            *self.__pages__,
            default=self._default,
            mode=self.__mode__,
            base_url=self.__base_url__ or "",
            preload=self._preload,
        )

    @computed_property
    def current_match(self):
        try:
            return self._compute_current_match()
        except Exception as e:
            for handler in self.on_route_error:
                if handler(e) is True:
                    return None
            raise

    def _compute_current_match(self) -> RouteMatch | None:
        current_path, search = self._get_current_path()
        if self.__mode__ == "history" and self.__base_url__:
            current_path = self._base_url_stripper(current_path)
        clean_path = current_path.strip("/")
        query = self._parse_query(search)
        history = self._resolve_history()
        state = history.state or {}

        for i, route in enumerate(self.__routes__):
            _, matcher, _, _, _ = route
            match = matcher(clean_path)
            if match:
                chain_entry = self.__chains__[i]
                groups = match.groups()
                per_level_params = self._split_params_by_level(groups, chain_entry.per_level_param_names)
                accumulated: dict[str, str] = {}
                for level_params in per_level_params:
                    accumulated.update(level_params)
                return RouteMatch(
                    path=current_path,
                    chain=chain_entry.chain,
                    per_level_params=tuple(per_level_params),
                    path_params=accumulated,
                    query=query,
                    state=state,
                )
        return None

    def _split_params_by_level(
        self,
        groups: tuple[str, ...],
        per_level_param_names: tuple[list[str], ...],
    ) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        offset = 0
        for level_names in per_level_param_names:
            count = len(level_names)
            level_params = dict(zip(level_names, groups[offset : offset + count], strict=True)) if level_names else {}
            result.append(level_params)
            offset += count
        return result

    def _parse_query(self, search: str) -> dict[str, str]:
        if not search:
            return {}
        # Deliberately drops empty-valued params (`?tab=` -> {}), preserving the
        # pre-existing query semantics used by level-identity comparisons.
        return {
            name: value
            for name, value in (
                [it[0], ""] if len(it) == 1 else it for it in (q.split("=", 2) for q in search.split("&"))
            )
            if name and value
        }

    def _resolve_history(self) -> HistoryPort:
        history = self._history
        if history is None:
            from webcompy.di import inject
            from webcompy.ports._keys import HISTORY_PORT_KEY

            history = inject(HISTORY_PORT_KEY)
            self._history = history
            self.__mode__ = history.mode
            history.set_navigation_callback(self.__set_path__)
        return history  # type: ignore[return-value]

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

    def _generate_router_context(
        self,
        pathname: str,
        search: str,
        match: Match[str] | None,
        path_param_names: list[str],
    ):
        history = self._resolve_history()
        query = self._parse_query(search)
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

    def _generate_routes(self, pages: Sequence[RouterPage]) -> tuple[list[RouteType], list[ChainEntry]]:
        routes: list[RouteType] = []
        chains: list[ChainEntry] = []
        for page in pages:
            for full_path, chain, per_level_param_names in self._walk_page_tree(page, "", (), ()):
                full_matcher = self._generate_route_matcher(full_path)
                full_param_names: list[str] = []
                for level_names in per_level_param_names:
                    full_param_names.extend(level_names)
                leaf_node = chain[-1]
                routes.append((full_path, full_matcher, full_param_names, leaf_node.component, leaf_node.page))
                chains.append(ChainEntry(full_path, chain, per_level_param_names))
        return routes, chains

    def _walk_page_tree(
        self,
        page: RouterPage,
        parent_accumulated: str,
        chain_so_far: tuple[RouteNode, ...],
        param_names_so_far: tuple[list[str], ...],
    ):
        segment = page["path"].strip("/")
        if segment:
            accumulated = f"{parent_accumulated}/{segment}" if parent_accumulated else segment
        else:
            accumulated = parent_accumulated

        node = RouteNode(segment=segment, component=page["component"], page=page)
        level_param_names = _get_path_params(segment)
        chain = (*chain_so_far, node)
        all_param_names = (*param_names_so_far, level_param_names)

        children = page.get("children")
        if children:
            for child in children:
                yield from self._walk_page_tree(child, accumulated, chain, all_param_names)
        else:
            yield (accumulated, chain, all_param_names)

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

        def _collect_lazy(pages):
            seen: set[int] = set()
            for page in pages:
                comp = page["component"]
                if (
                    isinstance(comp, LazyComponentGenerator)
                    and comp._resolved is None
                    and not comp._resolve_error
                    and id(comp) not in seen
                ):
                    seen.add(id(comp))
                    yield comp
                children = page.get("children")
                if children:
                    yield from _collect_lazy(children)

        lazy_components = list(_collect_lazy(self.__pages__))
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
