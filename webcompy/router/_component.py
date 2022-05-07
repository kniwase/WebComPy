from typing import Any, Tuple, Type, TypeAlias, TypeVar
from webcompy.components._abstract import TypedComponentBase
from webcompy.router._context import RouterContext, TypedRouterContext
from webcompy.router._link import TypedRouterLink


RoutedComponent: TypeAlias = TypedComponentBase(RouterContext)


ParamsType = TypeVar("ParamsType")
QueryParamsType = TypeVar("QueryParamsType")
PathParamsType = TypeVar("PathParamsType")

TypedRoute: TypeAlias = Tuple[
    Type[TypedRouterContext[ParamsType, QueryParamsType, PathParamsType]],
    Type[TypedRouterLink[ParamsType, QueryParamsType, PathParamsType]],
]


def create_typed_route(
    *,
    params_type: Type[ParamsType] = dict[str, Any],
    query_type: Type[QueryParamsType] = dict[str, str],
    path_params_type: Type[PathParamsType] = dict[str, str],
) -> TypedRoute[ParamsType, QueryParamsType, PathParamsType]:
    return (
        TypedRouterContext[ParamsType, QueryParamsType, PathParamsType],
        TypedRouterLink[ParamsType, QueryParamsType, PathParamsType],
    )
