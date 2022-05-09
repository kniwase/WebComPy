import logging
from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    List,
    TypeAlias,
    TypeVar,
    Union,
    cast,
)
import urllib.parse
from webcompy.reactive import ReactiveBase, computed_property
from webcompy.elements.types._element import Element
from webcompy.elements.typealias._element_property import (
    ElementChildren,
    AttrValue,
)
from webcompy.elements._dom_objs import DOMEvent
from webcompy.router._router import Router
from webcompy.router._pages import WebComPyRouterException
from webcompy._browser._modules import browser
from webcompy.utils._serialize import is_json_seriarizable


ParamsType = TypeVar("ParamsType")
QueryParamsType = TypeVar("QueryParamsType")
PathParamsType = TypeVar("PathParamsType")


class TypedRouterLink(Generic[ParamsType, QueryParamsType, PathParamsType], Element):
    _router: ClassVar[Union[Router, None]] = None
    _base_url: ClassVar[str]

    _query: ReactiveBase[dict[str, str]] | None
    _params: ReactiveBase[dict[str, Any]] | None
    _path_params: ReactiveBase[dict[str, str]] | None

    def __init__(
        self,
        *,
        to: Union[str, ReactiveBase[str]],
        text: List[Union[str, ReactiveBase[Any]]],
        params: ReactiveBase[ParamsType] | None = None,
        query: ReactiveBase[QueryParamsType] | None = None,
        path_params: ReactiveBase[PathParamsType] | None = None,
        attrs: Dict[str, AttrValue] | None = None,
    ) -> None:
        if TypedRouterLink._router is None:
            raise WebComPyRouterException("'Router' instance is not declarated.")
        self._given_attrs = attrs
        self._to = to
        self._query = (
            cast(ReactiveBase[dict[str, str]], query) if query is not None else None
        )
        self._params = (
            cast(ReactiveBase[dict[str, Any]], params) if params is not None else None
        )
        self._path_params = (
            cast(ReactiveBase[dict[str, str]], path_params)
            if path_params is not None
            else None
        )
        self._text = text
        super().__init__(
            "a",
            attrs=self._generate_attrs(),
            events={"click": self._on_click},
            children=self._generate_children(),
        )
        if isinstance(self._to, ReactiveBase):
            self._to.on_after_updating(self._refresh)

    @staticmethod
    def __set_router__(router: Router | None):
        TypedRouterLink._router = router

    def _refresh(self, *_: Any):
        self._attrs = self._generate_attrs()
        self._event_handlerst = {"click": self._on_click}
        self._init_children(self._generate_children())
        self._render()

    def _generate_children(self) -> list[ElementChildren]:
        return cast(list[ElementChildren], self._text)

    def _on_click(self, ev: DOMEvent) -> None:
        ev.preventDefault()
        if not TypedRouterLink._router:
            raise WebComPyRouterException("'Router' instance is not declarated.")
        if self._query is not None:
            if not isinstance(self._query, ReactiveBase) or not isinstance(self._query.value, dict):  # type: ignore
                raise WebComPyRouterException(
                    "Argument 'query' of RouterLink must be Reactive Object of Dict."
                )
            if any(not isinstance(k, str) for k in self._query.value.keys()):  # type: ignore
                raise WebComPyRouterException(
                    "Keys of Argument 'query' of RouterLink must be str."
                )
            if any(not isinstance(v, str) for v in self._query.value.values()):  # type: ignore
                raise WebComPyRouterException(
                    "Values of Argument 'query' of RouterLink must be str."
                )
        if self._params is not None:
            if not isinstance(self._params, ReactiveBase) or not isinstance(self._params.value, dict):  # type: ignore
                raise WebComPyRouterException(
                    "Argument 'params' of RouterLink must be Reactive Object of Dict."
                )
            if any(not isinstance(k, str) for k in self._params.value.keys()):  # type: ignore
                raise WebComPyRouterException(
                    "Keys of Argument 'params' of RouterLink must be str."
                )
        if not browser:
            return
        href: str = ev.currentTarget.attrs["href"]
        current_path = (
            browser.window.location.pathname
            if TypedRouterLink._router.__mode__ == "history"
            else browser.window.location.hash
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
                    logging.warn(
                        "Argument 'params' of RouterLink should be a Reactive Object of json-serializable dict."
                    )
            browser.window.history.pushState(
                state,
                browser.javascript.NULL,
                href,
            )
            TypedRouterLink._router.__set_path__(href, params)

    def _generate_attrs(self) -> dict[str, AttrValue]:
        attrs = self._given_attrs if self._given_attrs else {}
        return {
            **attrs,
            "href": self._href,
            "webcompy-routerlink": True,
        }

    @computed_property
    def _href(self) -> str:
        to = self._to.value if isinstance(self._to, ReactiveBase) else self._to
        if self._path_params is not None:
            to = to.format(**self._path_params.value)
        path_encoded = "/".join(map(urllib.parse.quote, to.strip("/").split("/")))
        to = f"/{path_encoded}/" if path_encoded else "/"
        query_encoded = urllib.parse.urlencode(self._query.value if self._query else {})
        query = "?" + query_encoded if query_encoded else ""
        if TypedRouterLink._router:
            if TypedRouterLink._router.__mode__ == "hash":
                return "#" + to + query
            elif TypedRouterLink._router.__base_url__:
                return "/" + TypedRouterLink._router.__base_url__ + to + query
            else:
                return to + query
        else:
            return to + query


RouterLink: TypeAlias = TypedRouterLink[dict[str, Any], dict[str, str], dict[str, str]]
