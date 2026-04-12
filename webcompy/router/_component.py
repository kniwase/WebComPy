from __future__ import annotations

from typing import Any, TypeAlias, TypeVar

from webcompy.components._abstract import TypedComponentBase
from webcompy.router._context import RouterContext, TypedRouterContext
from webcompy.router._link import TypedRouterLink

RoutedComponent: TypeAlias = TypedComponentBase(RouterContext)


ParamsType = TypeVar("ParamsType")
QueryParamsType = TypeVar("QueryParamsType")
PathParamsType = TypeVar("PathParamsType")

TypedRoute: TypeAlias = tuple[
    type[TypedRouterContext[ParamsType, QueryParamsType, PathParamsType]],
    type[TypedRouterLink[ParamsType, QueryParamsType, PathParamsType]],
]


def create_typed_route(
    *,
    params_type: type[ParamsType] = dict[str, Any],
    query_type: type[QueryParamsType] = dict[str, str],
    path_params_type: type[PathParamsType] = dict[str, str],
) -> TypedRoute[ParamsType, QueryParamsType, PathParamsType]:
    return (
        TypedRouterContext[ParamsType, QueryParamsType, PathParamsType],
        TypedRouterLink[ParamsType, QueryParamsType, PathParamsType],
    )
