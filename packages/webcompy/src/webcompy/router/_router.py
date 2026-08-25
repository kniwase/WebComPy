"""Application router with nested pages, guards, and history integration."""

from __future__ import annotations

import inspect
import urllib.parse
from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from itertools import count
from re import Match
from re import compile as re_compile
from re import escape as re_escape
from typing import (
    Any,
    Literal,
    TypeAlias,
)

from webcompy.aio._aio import _log_error, resolve_async
from webcompy.components import ComponentGenerator
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.ports._history import HistoryPort
from webcompy.router._context import RouterContext, TypedRouterContext
from webcompy.router._pages import RouterPage, WebComPyRouterException
from webcompy.signal import computed_property

RouteType: TypeAlias = tuple[
    str,
    Callable[[str], Match[str] | None],
    list[str],
    ComponentGenerator[RouterContext],
    RouterPage,
]

GuardResult: TypeAlias = bool | str | None
BeforeRouteGuard: TypeAlias = Callable[[str, str], GuardResult | Awaitable[GuardResult]]

_REDIRECT_DEPTH_LIMIT = 10


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
    """Route table with nested page chains and navigation hooks.

    Builds flat route matchers from nested ``RouterPage`` declarations,
    resolves the current match reactively, and runs an async-capable
    guard pipeline before committing navigations through the history
    port.

    Args:
        *pages: Route page declarations.
        default: Component rendered when no route matches, or ``None``
            for a "Not Found" fallback.
        history: History port driving the current path. When ``None``,
            the port is resolved from the DI scope on first use.
        mode: Routing mode (``"hash"`` or ``"history"``). Ignored when
            ``history`` is provided.
        base_url: Leading path segment stripped from paths in
            ``"history"`` mode.
        preload: Whether lazy routes are preloaded when the router
            starts.

    Attributes:
        before_route_change: Hooks run before a route change commits.
        after_route_change: Hooks run after a route change committed.
        on_route_error: Handlers invoked when route resolution or guard
            execution fails.
        current_match: ``Computed[RouteMatch | None]`` for the active
            path; ``None`` when no route matches.

    """

    _history: HistoryPort | None
    __mode__: Literal["hash", "history"]
    __routes__: list[RouteType]
    __chains__: list[ChainEntry]
    __pages__: tuple[RouterPage, ...]
    __route_variants__: list[list[dict[str, str]] | None]

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
            history.set_navigation_callback(self._on_browser_navigation)
        self.__base_url__ = base_url.strip().strip("/")
        self._base_url_stripper = partial(re_compile("^" + re_escape("/" + self.__base_url__)).sub, "")
        self.__routes__, self.__chains__, self.__route_variants__ = self._generate_routes(pages)
        self._default = default
        self._preload = preload
        self.before_route_change: list[BeforeRouteGuard] = []
        self.after_route_change: list[Callable[[str], None]] = []
        self.on_route_error: list[Callable[[Exception], bool | None]] = []
        self._nav_token_counter = count(1)
        self._latest_token = 0

    def _clone_for_request(self) -> Router:
        router = Router(
            *self.__pages__,
            default=self._default,
            mode=self.__mode__,
            base_url=self.__base_url__ or "",
            preload=self._preload,
        )
        router.before_route_change = list(self.before_route_change)
        router.after_route_change = list(self.after_route_change)
        router.on_route_error = list(self.on_route_error)
        return router

    @computed_property
    def current_match(self):
        """Current match for the active path.

        Returns:
            A ``Computed[RouteMatch | None]`` whose ``.value`` is the
            matching ``RouteMatch``, or ``None`` when no route matches
            the current path.

        Raises:
            Exception: If route matching raises and no ``on_route_error``
                handler suppresses the error.

        """
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
            history.set_navigation_callback(self._on_browser_navigation)
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

    def _generate_routes(
        self, pages: Sequence[RouterPage]
    ) -> tuple[list[RouteType], list[ChainEntry], list[list[dict[str, str]] | None]]:
        routes: list[RouteType] = []
        chains: list[ChainEntry] = []
        variants: list[list[dict[str, str]] | None] = []
        for page in pages:
            for full_path, chain, per_level_param_names in self._walk_page_tree(page, "", (), ()):
                full_matcher = self._generate_route_matcher(full_path)
                full_param_names: list[str] = []
                for level_names in per_level_param_names:
                    full_param_names.extend(level_names)
                leaf_node = chain[-1]
                routes.append((full_path, full_matcher, full_param_names, leaf_node.component, leaf_node.page))
                chains.append(ChainEntry(full_path, chain, per_level_param_names))
                variants.append(self._compute_route_variants(chain))
        return routes, chains, variants

    @staticmethod
    def _compute_route_variants(chain: tuple[RouteNode, ...]) -> list[dict[str, str]] | None:
        variants: list[dict[str, str]] = [{}]
        for node in chain:
            path_params = node.page.get("path_params")
            if not path_params:
                continue
            merged: list[dict[str, str]] = []
            for params in path_params:
                for base in variants:
                    merged.append({**base, **params})
            variants = merged
        return None if variants == [{}] else variants

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

    def __set_path__(self, path: str, state: dict[str, Any] | None) -> None:
        token = next(self._nav_token_counter)
        self._latest_token = token
        try:
            self._attempt(path, state, token, redirect_depth=0, is_redirect=False)
        except Exception as exc:
            if not self._suppress_route_error(exc):
                raise

    def _on_browser_navigation(self, path: str, state: dict[str, Any] | None) -> None:
        """Handle popstate navigations: the browser already owns the URL.

        No guards run and no URL is written; pending async chains are
        superseded so they cannot override the browser's own navigation.
        The incoming browser path is normalized so the stored value always
        matches the canonical format used by app-initiated navigations.
        """
        self._latest_token = next(self._nav_token_counter)
        history = self._resolve_history()
        normalized = self._normalize_app_path(path)
        history.navigate(normalized, state)
        for callback in self.after_route_change:
            callback(normalized)

    def _normalize_app_path(self, path: str) -> str:
        if self.__mode__ == "hash" and path.startswith("#"):
            path = path[1:]
        if self.__mode__ == "history" and self.__base_url__:
            path = self._base_url_stripper(path)
        pathname, sep, query = path.partition("?")
        # Normalize the pathname to a trailing-slash format so the stored
        # path always matches the browser URL built by HistoryPort
        # (_build_url emits a trailing slash). Without this, a programmatic
        # navigation without a trailing slash would observe a different path
        # on a later popstate and re-trigger navigation.
        if pathname and not pathname.endswith("/"):
            pathname += "/"
        return pathname + sep + query

    def _attempt(
        self,
        path: str,
        state: dict[str, Any] | None,
        token: int,
        redirect_depth: int,
        is_redirect: bool,
    ) -> None:
        if redirect_depth > _REDIRECT_DEPTH_LIMIT:
            raise WebComPyRouterException("redirect loop detected (more than 10 redirects)")
        history = self._resolve_history()
        from_path = self._normalize_app_path(history.value)
        to_path = self._normalize_app_path(path)
        guards = list(self.before_route_change)
        for index, guard in enumerate(guards):
            result = guard(from_path, to_path)
            if inspect.isawaitable(result):
                resolve_async(
                    self._continue_async(
                        result,
                        guards[index + 1 :],
                        from_path,
                        to_path,
                        state,
                        token,
                        redirect_depth,
                        is_redirect,
                    ),
                    on_error=self._log_unsuppressed_route_error,
                )
                return
            if not self._interpret(result, token, redirect_depth):
                return
        self._commit(to_path, state, token, is_redirect)

    async def _continue_async(
        self,
        pending: Awaitable[GuardResult],
        remaining: list[BeforeRouteGuard],
        from_path: str,
        to_path: str,
        state: dict[str, Any] | None,
        token: int,
        redirect_depth: int,
        is_redirect: bool,
    ) -> None:
        result = await pending
        if token != self._latest_token:
            return
        if not self._interpret(result, token, redirect_depth):
            return
        for guard in remaining:
            result = guard(from_path, to_path)
            if inspect.isawaitable(result):
                result = await result
                if token != self._latest_token:
                    return
            if not self._interpret(result, token, redirect_depth):
                return
        self._commit(to_path, state, token, is_redirect)

    def _interpret(self, result: GuardResult, token: int, redirect_depth: int) -> bool:
        if isinstance(result, str):
            if token != self._latest_token:
                return False
            self._attempt(result, None, token, redirect_depth + 1, is_redirect=True)
            return False
        return result is not False

    def _commit(
        self,
        to_path: str,
        state: dict[str, Any] | None,
        token: int,
        is_redirect: bool,
    ) -> None:
        if token != self._latest_token:
            return
        history = self._resolve_history()
        if is_redirect:
            history.replace_url(to_path, state)
        elif self._normalize_app_path(history.value) != to_path:
            history.push_url(to_path, state)
        history.navigate(to_path, state)
        for callback in self.after_route_change:
            callback(to_path)

    def _suppress_route_error(self, exc: Exception) -> bool:
        return any(handler(exc) is True for handler in self.on_route_error)

    def _log_unsuppressed_route_error(self, exc: Exception) -> None:
        if not self._suppress_route_error(exc):
            _log_error(exc)

    def preload_lazy_routes(self, *, force: bool = False) -> None:
        """Resolve lazy route components ahead of navigation.

        Resolves all ``LazyComponentGenerator`` pages so their modules
        load without delaying later navigations.

        Args:
            force: Resolve even when ``preload`` was disabled at
                construction.

        """
        if not self._preload and not force:
            return
        from webcompy.di import inject
        from webcompy.di._keys import _APP_KEY
        from webcompy.ports._keys import HOST_PORT_KEY
        from webcompy.router._lazy import LazyComponentGenerator
        from webcompy.utils._environment import ENVIRONMENT

        app = inject(_APP_KEY, default=None)
        seen: set[int] = set()

        def _collect_lazy(pages):
            for page in pages:
                comp = page["component"]
                if isinstance(comp, LazyComponentGenerator) and not comp._resolve_error and id(comp) not in seen:
                    seen.add(id(comp))
                    yield comp
                children = page.get("children")
                if children:
                    yield from _collect_lazy(children)

        lazy_components = list(_collect_lazy(self.__pages__))
        if lazy_components:
            if app is not None:
                app._record_phase("lazy_preload_start")
            if ENVIRONMENT == "pyscript":

                def _batch_preload(components=lazy_components):
                    for c in components:
                        with suppress(Exception):
                            c._preload()
                    if app is not None:
                        app._record_phase("lazy_preloaded")

                inject(HOST_PORT_KEY).schedule_macro_task(_batch_preload)
            else:
                for c in lazy_components:
                    with suppress(Exception):
                        c._preload()
                if app is not None:
                    app._record_phase("lazy_preloaded")

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
