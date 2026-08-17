from __future__ import annotations

import inspect
import itertools
import typing
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.hydration._transfer_meta import BUILTIN_META_TAGS, _qualified_type_name

DEFAULT_RPC_PATH = "/_webcompy-rpc"


@dataclass(frozen=True)
class ProcedureInfo:
    name: str
    func: Callable[..., Any]
    param_schemas: dict[str, Any]
    param_order: list[str]
    required: frozenset[str]
    result_schema: Any
    is_async: bool


class ProcedureRegistry:
    def __init__(self, *, base_url: str = "/") -> None:
        self._path = DEFAULT_RPC_PATH
        self._base_url = base_url
        self._procedures: dict[str, ProcedureInfo] = {}
        self._type_handlers: dict[str, tuple[type, Callable[[Any], Any], Callable[[Any], Any]]] = {}
        self._meta_encoders: dict[type, tuple[str, Callable[[Any], Any]]] = {}
        self._meta_decoders: dict[str, Callable[[Any], Any]] = {}
        self._id_counter = itertools.count(1)

    @property
    def path(self) -> str:
        return self._path

    @property
    def endpoint_url(self) -> str:
        if self._base_url == "/":
            return self._path
        return self._base_url.rstrip("/") + self._path

    def set_path(self, path: str) -> None:
        if not path.startswith("/") or path == "/":
            raise WebComPyException(f"RPC path must be an absolute non-root path, got {path!r}")
        self._path = path

    @property
    def has_procedures(self) -> bool:
        return bool(self._procedures)

    def next_id(self) -> int:
        return next(self._id_counter)

    def get(self, name: str) -> ProcedureInfo | None:
        return self._procedures.get(name)

    def procedure(self, func: Callable[..., Any]) -> Callable[..., Any]:
        self.register(func.__name__, func)
        return func

    def register(self, name: str, func: Callable[..., Any]) -> None:
        if name in self._procedures:
            raise WebComPyException(f"RPC procedure {name!r} is already registered")
        try:
            hints = typing.get_type_hints(func)
        except Exception as err:
            raise WebComPyException(f"RPC procedure {name!r}: failed to resolve type hints: {err}") from err
        signature = inspect.signature(func)
        param_schemas: dict[str, Any] = {}
        param_order: list[str] = []
        untyped: list[str] = []
        for param_name, param in signature.parameters.items():
            if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
                raise WebComPyException(f"RPC procedure {name!r}: variadic parameter {param_name!r} is not allowed")
            if param_name not in hints:
                untyped.append(param_name)
                continue
            param_schemas[param_name] = hints[param_name]
            param_order.append(param_name)
        if untyped:
            raise WebComPyException(f"RPC procedure {name!r}: untyped parameter(s): {', '.join(untyped)}")
        if "return" not in hints:
            raise WebComPyException(f"RPC procedure {name!r}: missing return type annotation")
        required = frozenset(
            param_name for param_name, param in signature.parameters.items() if param.default is inspect.Parameter.empty
        )
        self._procedures[name] = ProcedureInfo(
            name=name,
            func=func,
            param_schemas=param_schemas,
            param_order=param_order,
            required=required,
            result_schema=hints["return"],
            is_async=inspect.iscoroutinefunction(func),
        )

    def register_type_handler(
        self,
        cls: type,
        encoder: Callable[[Any], Any],
        decoder: Callable[[Any], Any],
    ) -> None:
        tag = _qualified_type_name(cls)
        self._type_handlers[tag] = (cls, encoder, decoder)
        self._meta_encoders[cls] = (tag, encoder)
        self._meta_decoders[tag] = decoder

    @property
    def meta_encoders(self) -> dict[type, tuple[str, Callable[[Any], Any]]]:
        return self._meta_encoders

    @property
    def meta_decoders(self) -> dict[str, Callable[[Any], Any]]:
        return self._meta_decoders

    def is_known_meta_tag(self, tag: str) -> bool:
        return tag in BUILTIN_META_TAGS or tag in self._type_handlers


__all__ = [
    "DEFAULT_RPC_PATH",
    "ProcedureInfo",
    "ProcedureRegistry",
]
