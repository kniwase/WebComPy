"""Typed route helper pairing a router context with its link type."""

from __future__ import annotations

from typing import Any, TypeAlias, TypeVar

from webcompy.components._libs import ComponentContext
from webcompy.router._context import RouterContext, TypedRouterContext
from webcompy.router._link import TypedRouterLink

RoutedComponent = ComponentContext[RouterContext]
"""Component context of a component rendered by the router with a ``RouterContext``."""


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
    """Build a typed ``(context, link)`` pair for route declarations.

    The returned tuple parameterizes ``TypedRouterContext`` and
    ``TypedRouterLink`` with the given param types.

    Args:
        params_type: Type of the navigation state param dict.
        query_type: Type of the query param dict.
        path_params_type: Type of the path param dict.

    Returns:
        A tuple of the matching ``TypedRouterContext`` and
        ``TypedRouterLink`` parameterizations.

    """
    return (
        TypedRouterContext[ParamsType, QueryParamsType, PathParamsType],
        TypedRouterLink[ParamsType, QueryParamsType, PathParamsType],
    )
