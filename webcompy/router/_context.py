from typing import Any, Generic, NoReturn, TypeAlias, TypeVar, final


ParamsType = TypeVar("ParamsType")
QueryParamsType = TypeVar("QueryParamsType")
PathParamsType = TypeVar("PathParamsType")


class TypedRouterContext(Generic[ParamsType, QueryParamsType, PathParamsType]):
    __path: str
    __state_params: ParamsType
    __query_params: QueryParamsType
    __path_params: PathParamsType

    @final
    def __init__(self) -> NoReturn:
        raise NotImplementedError(
            "RouterContext cannot generate an instance by constructor"
        )

    @classmethod
    def __create_instance__(
        cls,
        *,
        path: str,
        state: ParamsType,
        query_params: QueryParamsType,
        path_params: PathParamsType,
    ):
        instance = cls.__new__(cls)
        instance.__path = path
        instance.__query_params = query_params
        instance.__path_params = path_params
        instance.__state_params = state
        return instance

    @property
    def path(self):
        return self.__path

    @property
    def path_params(self):
        return self.__path_params

    @property
    def query(self):
        return self.__query_params

    @property
    def params(self):
        return self.__state_params

    def __repr__(self):
        return (
            "RouterContext("
            + ", ".join(
                f"{name}={repr(getattr(self, name))}"
                for name in ("path", "query", "path_params", "params")
            )
            + ")"
        )


RouterContext: TypeAlias = TypedRouterContext[
    dict[str, Any], dict[str, str], dict[str, str]
]
