from __future__ import annotations

import logging
import urllib.parse
from typing import (
    Any,
    Generic,
    TypeAlias,
    TypeVar,
    cast,
)

from webcompy._browser._modules import browser
from webcompy.di import inject
from webcompy.di._exceptions import InjectionError
from webcompy.di._keys import _ROUTER_KEY
from webcompy.elements._dom_objs import DOMEvent
from webcompy.elements.typealias._element_property import (
    AttrValue,
    ElementChildren,
)
from webcompy.elements.types._element import Element
from webcompy.router._pages import WebComPyRouterException
from webcompy.router._router import Router
from webcompy.signal import SignalBase, computed_property
from webcompy.utils._serialize import is_json_seriarizable

ParamsType = TypeVar("ParamsType")
QueryParamsType = TypeVar("QueryParamsType")
PathParamsType = TypeVar("PathParamsType")


class TypedRouterLink(Generic[ParamsType, QueryParamsType, PathParamsType], Element):
    _query: SignalBase[dict[str, str]] | None
    _params: SignalBase[dict[str, Any]] | None
    _path_params: SignalBase[dict[str, str]] | None

    def __init__(
        self,
        *,
        to: str | SignalBase[str],
        text: list[str | SignalBase[Any]],
        params: SignalBase[ParamsType] | None = None,
        query: SignalBase[QueryParamsType] | None = None,
        path_params: SignalBase[PathParamsType] | None = None,
        attrs: dict[str, AttrValue] | None = None,
    ) -> None:
        try:
            router = inject(_ROUTER_KEY)
        except InjectionError:
            raise WebComPyRouterException("'Router' instance is not provided via DI.") from None
        self._given_attrs = attrs
        self._to = to
        self._query = cast("SignalBase[dict[str, str]]", query) if query is not None else None
        self._params = cast("SignalBase[dict[str, Any]]", params) if params is not None else None
        self._path_params = cast("SignalBase[dict[str, str]]", path_params) if path_params is not None else None
        self._text = text
        self._router = router
        super().__init__(
            "a",
            attrs=self._generate_attrs(),
            events={"click": self._on_click},
            children=self._generate_children(),
        )
        if isinstance(self._to, SignalBase):
            self._add_callback_node(self._to.on_after_updating(self._refresh))

    @staticmethod
    def __set_router__(router: Router | None):
        pass

    def _refresh(self, *_: Any):
        self._attrs = self._generate_attrs()
        self._event_handlers = {"click": self._on_click}
        self._init_children(self._generate_children())
        self._render()

    def _generate_children(self) -> list[ElementChildren]:
        return cast("list[ElementChildren]", self._text)

    def _on_click(self, ev: DOMEvent) -> None:
        ev.preventDefault()
        if self._query is not None:
            if not isinstance(self._query, SignalBase) or not isinstance(self._query.value, dict):  # type: ignore
                raise WebComPyRouterException("Argument 'query' of RouterLink must be Signal Object of Dict.")
            if any(not isinstance(k, str) for k in self._query.value):  # type: ignore
                raise WebComPyRouterException("Keys of Argument 'query' of RouterLink must be str.")
            if any(not isinstance(v, str) for v in self._query.value.values()):  # type: ignore
                raise WebComPyRouterException("Values of Argument 'query' of RouterLink must be str.")
        if self._params is not None:
            if not isinstance(self._params, SignalBase) or not isinstance(self._params.value, dict):  # type: ignore
                raise WebComPyRouterException("Argument 'params' of RouterLink must be Signal Object of Dict.")
            if any(not isinstance(k, str) for k in self._params.value):  # type: ignore
                raise WebComPyRouterException("Keys of Argument 'params' of RouterLink must be str.")
        if not browser:
            return
        href: str = ev.currentTarget.getAttribute("href")
        current_path = (
            browser.window.location.pathname if self._router.__mode__ == "history" else browser.window.location.hash
        )
        if current_path != href:
            if self._params is None:
                state = None
                params = None
            else:
                params = dict(self._params.value.items())
                if is_json_seriarizable(self._params.value):
                    state = params
                else:
                    state = None
                    logging.warn("Argument 'params' of RouterLink should be a Signal Object of json-serializable dict.")
            browser.window.history.pushState(state, None, href)
            self._router.__set_path__(href, params)

    def _generate_attrs(self) -> dict[str, AttrValue]:
        attrs = self._given_attrs if self._given_attrs else {}
        return {
            **attrs,
            "href": self._href,
            "webcompy-routerlink": True,
        }

    @computed_property
    def _href(self) -> str:
        to = self._to.value if isinstance(self._to, SignalBase) else self._to
        if self._path_params is not None:
            to = to.format(**self._path_params.value)
        path_encoded = "/".join(map(urllib.parse.quote, to.strip("/").split("/")))
        to = f"/{path_encoded}/" if path_encoded else "/"
        query_encoded = urllib.parse.urlencode(self._query.value if self._query else {})
        query = "?" + query_encoded if query_encoded else ""
        if self._router.__mode__ == "hash":
            return "#" + to + query
        elif self._router.__base_url__:
            return "/" + self._router.__base_url__ + to + query
        else:
            return to + query


RouterLink: TypeAlias = TypedRouterLink[dict[str, Any], dict[str, str], dict[str, str]]
