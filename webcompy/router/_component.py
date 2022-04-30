from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Tuple,
    Type,
    TypeAlias,
    TypeVar,
    Union,
)
from webcompy.reactive import ReactiveBase, computed
from webcompy.elements.typealias._element_property import AttrValue
from webcompy.components._abstract import TypedComponentBase
from webcompy.components._generator import ComponentGenerator
from webcompy.router._context import RouterContext, TypedRouterContext
from webcompy.router._link import TypedRouterLink as Base
from webcompy.router._pages import RouterPage


RoutedComponent: TypeAlias = TypedComponentBase(RouterContext)


ParamsType = TypeVar("ParamsType")
QueryParamsType = TypeVar("QueryParamsType")
PathParamsType = TypeVar("PathParamsType")


class RouterLink(
    Generic[ParamsType, QueryParamsType, PathParamsType],
    Base[ParamsType, QueryParamsType],
):
    _path: str

    def __init__(
        self,
        *,
        text: List[Union[str, ReactiveBase[Any]]],
        params: ReactiveBase[ParamsType] | None = None,
        query: ReactiveBase[QueryParamsType] | None = None,
        path_params: ReactiveBase[PathParamsType] | None = None,
        attrs: Dict[str, AttrValue] | None = None,
    ) -> None:
        if path_params:
            to = computed(lambda: self._path.format(**path_params.value))
        else:
            to = self._path
        super().__init__(to=to, text=text, params=params, query=query, attrs=attrs)


TypedRoute: TypeAlias = Tuple[
    Type[TypedRouterContext[ParamsType, QueryParamsType, PathParamsType]],
    Type[RouterLink[ParamsType, QueryParamsType, PathParamsType]],
    Callable[
        [
            ComponentGenerator[
                TypedRouterContext[ParamsType, QueryParamsType, PathParamsType]
            ]
        ],
        RouterPage,
    ],
]


def create_typed_route(
    path: str,
    *,
    params_type: Type[ParamsType] = dict[str, Any],
    query_type: Type[QueryParamsType] = dict[str, str],
    path_params_type: Type[PathParamsType] = dict[str, str],
    router_meta: Any = None,
) -> TypedRoute[ParamsType, QueryParamsType, PathParamsType]:
    _ParamsType = TypeVar("_ParamsType")
    _QueryParamsType = TypeVar("_QueryParamsType")
    _PathParamsType = TypeVar("_PathParamsType")

    class TypedRouterLink(RouterLink[_ParamsType, _QueryParamsType, _PathParamsType]):
        _path: str = path

    return (
        TypedRouterContext[ParamsType, QueryParamsType, PathParamsType],
        TypedRouterLink[ParamsType, QueryParamsType, PathParamsType],
        lambda component_generator: {"path": path, "component": component_generator},
    )
