from __future__ import annotations

import dis
import inspect
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, overload

from webcompy.signal._base import Signal
from webcompy.signal._dict import ReactiveDict
from webcompy.signal._list import ReactiveList

T = TypeVar("T")
V = TypeVar("V")
K = TypeVar("K")


_FACTORY_ARG_MSG = "Factory appears to require arguments; use a zero-argument callable"
_MISSING = object()
_AUTO_KEY_COLLISION_MSG_FMT = (
    "Auto-key collision detected at {filename}:{lineno} with {previous_key}. Use an explicit key to disambiguate."
)
_EXPLICIT_KEY_COLLISION_MSG_FMT = (
    "Duplicate explicit key '{key}' in {component_name}. Use a unique key for each composable call."
)
_WEBCOMY_DIR = __name__.split(".")[0]


@dataclass(frozen=True)
class AutoKey:
    filename: str
    lineno: int
    col: int | None
    explicit: bool = False

    def __str__(self) -> str:
        if self.explicit:
            return self.filename
        if self.col is None:
            return f"{self.filename}:{self.lineno}"
        return f"{self.filename}:{self.lineno}:{self.col}"

    @classmethod
    def from_explicit(cls, key: str) -> AutoKey:
        return cls(key, 0, None, explicit=True)


def _user_caller_frame() -> Any:
    frame = inspect.currentframe()
    if frame is None:
        return None
    try:
        candidate = frame.f_back
        while candidate is not None:
            mod = candidate.f_globals.get("__name__", "")
            if not mod.startswith(_WEBCOMY_DIR):
                return candidate
            candidate = candidate.f_back
        return None
    finally:
        del frame


def _auto_key() -> AutoKey:
    caller_frame = _user_caller_frame()
    if caller_frame is None:
        return AutoKey("_unknown_", 0, None)
    filename = caller_frame.f_code.co_filename
    lineno = caller_frame.f_lineno
    col: int | None = None
    lasti = getattr(caller_frame, "f_lasti", -1)
    try:
        instructions = list(dis.get_instructions(caller_frame.f_code))
        for i, instr in enumerate(instructions):
            next_offset = instructions[i + 1].offset if i + 1 < len(instructions) else instr.offset + 2
            if instr.offset <= lasti < next_offset:
                positions = getattr(instr, "positions", None)
                if positions is not None:
                    start_col = getattr(positions, "col_offset", None)
                    if start_col is not None:
                        col = start_col
                break
    except Exception:
        pass
    key = AutoKey(filename, lineno, col)
    del caller_frame
    return key


def _resolve_args(
    factory_or_key: str | AutoKey | Callable[[], T],
    maybe_factory: Callable[[], T] | None,
) -> tuple[AutoKey, Callable[[], T]]:
    if isinstance(factory_or_key, AutoKey):
        if maybe_factory is None:
            raise TypeError("AutoKey passed as first argument requires explicit factory as second")
        return factory_or_key, maybe_factory
    if isinstance(factory_or_key, str):
        if maybe_factory is None:
            raise TypeError("Factory callable is required when an explicit key is provided")
        return AutoKey.from_explicit(factory_or_key), maybe_factory
    if maybe_factory is not None:
        raise TypeError(
            "use_state() / use_reactive_list() / use_reactive_dict() accept either "
            "(factory) or (key, factory); pass the factory positionally"
        )
    if not callable(factory_or_key):
        raise TypeError(
            "use_state() / use_reactive_list() / use_reactive_dict() require a zero-argument "
            f"factory callable as the first argument, got {type(factory_or_key).__name__}"
        )
    return _auto_key(), factory_or_key


def _try_resolve_payload_key(ctx: Any, key: AutoKey) -> Any:
    from webcompy.components._libs import generate_id
    from webcompy.di import inject
    from webcompy.di._keys import HYDRATION_SIGNAL_DATA_KEY

    payload = inject(HYDRATION_SIGNAL_DATA_KEY, default=None)
    if payload is None:
        return _MISSING
    component_id = generate_id(ctx._component_name)
    component_data = payload.get(component_id)
    if not component_data:
        return _MISSING
    return component_data.get(str(key), _MISSING)


def _get_active_component_context() -> Any:
    from webcompy.components._hooks import _active_component_context

    try:
        return _active_component_context.get()
    except LookupError:
        return None


def _validate_factory(factory: Callable[[], Any]) -> None:
    try:
        sig = inspect.signature(factory)
    except (TypeError, ValueError):
        return
    for param in sig.parameters.values():
        if param.default is inspect.Parameter.empty and param.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            warnings.warn(_FACTORY_ARG_MSG, UserWarning, stacklevel=3)
            return


def _register_transferable(ctx: Any, key: AutoKey, sig: Any) -> None:
    key_str = str(key)
    if key_str in ctx._transferable_signals:
        if key.explicit:
            warnings.warn(
                _EXPLICIT_KEY_COLLISION_MSG_FMT.format(
                    key=str(key),
                    component_name=ctx._component_name,
                ),
                UserWarning,
                stacklevel=3,
            )
        else:
            warnings.warn(
                _AUTO_KEY_COLLISION_MSG_FMT.format(
                    filename=key.filename,
                    lineno=key.lineno,
                    previous_key=key_str,
                ),
                UserWarning,
                stacklevel=3,
            )
        return
    ctx._transferable_signals[key_str] = sig


@overload
def use_state(factory: Callable[[], T]) -> Signal[T]: ...


@overload
def use_state(key: str, factory: Callable[[], T]) -> Signal[T]: ...


def use_state(  # type: ignore[no-redef]
    factory_or_key: str | Callable[[], T],
    maybe_factory: Callable[[], T] | None = None,
) -> Signal[T]:
    """Create a transfer-capable reactive Signal.

    Call inside a component setup function. On the server the factory
    runs to produce the initial value; during browser hydration the
    factory is skipped and the value is restored from the SSR transfer
    payload.  Outside component setup a ``UserWarning`` is emitted and
    the signal is created without transfer registration.

    Args:
        factory_or_key: A zero-argument factory callable, or an explicit
            string key when ``maybe_factory`` is also provided.
        maybe_factory: The zero-argument factory when the first argument
            is an explicit key.

    Returns:
        A ``Signal[T]`` registered for SSR transfer when called inside
        component setup.
    """
    key, factory = _resolve_args(factory_or_key, maybe_factory)
    _validate_factory(factory)

    ctx = _get_active_component_context()

    if ctx is not None:
        restored = _try_resolve_payload_key(ctx, key)
        if restored is not _MISSING:
            sig: Signal[T] = Signal(restored)
        else:
            sig = Signal(factory())
        _register_transferable(ctx, key, sig)
        return sig

    warnings.warn(
        "use_state() called outside component setup; signal will not be transferred",
        UserWarning,
        stacklevel=2,
    )
    return Signal(factory())


@overload
def use_reactive_list(factory: Callable[[], list[V]]) -> ReactiveList[V]: ...


@overload
def use_reactive_list(key: str, factory: Callable[[], list[V]]) -> ReactiveList[V]: ...


def use_reactive_list(  # type: ignore[no-redef]
    factory_or_key: str | Callable[[], list[V]],
    maybe_factory: Callable[[], list[V]] | None = None,
) -> ReactiveList[V]:
    """Create a transfer-capable ReactiveList.

    Same factory-skip semantics as ``use_state()`` but returns a
    ``ReactiveList[V]`` with working mutation methods (``append``,
    ``pop``, etc.).  Call inside a component setup function.
    """
    key, factory = _resolve_args(factory_or_key, maybe_factory)
    _validate_factory(factory)

    ctx = _get_active_component_context()

    if ctx is not None:
        restored = _try_resolve_payload_key(ctx, key)
        if restored is not _MISSING:
            rl: ReactiveList[V] = ReactiveList(restored)
        else:
            rl = ReactiveList(factory())
        _register_transferable(ctx, key, rl)
        return rl

    warnings.warn(
        "use_reactive_list() called outside component setup; list will not be transferred",
        UserWarning,
        stacklevel=2,
    )
    return ReactiveList(factory())


@overload
def use_reactive_dict(factory: Callable[[], dict[K, V]]) -> ReactiveDict[K, V]: ...


@overload
def use_reactive_dict(key: str, factory: Callable[[], dict[K, V]]) -> ReactiveDict[K, V]: ...


def use_reactive_dict(  # type: ignore[no-redef]
    factory_or_key: str | Callable[[], dict[K, V]],
    maybe_factory: Callable[[], dict[K, V]] | None = None,
) -> ReactiveDict[K, V]:
    """Create a transfer-capable ReactiveDict.

    Same factory-skip semantics as ``use_state()`` but returns a
    ``ReactiveDict[K, V]`` with working mutation methods (``__setitem__``,
    ``pop``, etc.).  Call inside a component setup function.
    """
    key, factory = _resolve_args(factory_or_key, maybe_factory)
    _validate_factory(factory)

    ctx = _get_active_component_context()

    if ctx is not None:
        restored = _try_resolve_payload_key(ctx, key)
        if restored is not _MISSING:
            rd: ReactiveDict[K, V] = ReactiveDict(restored)
        else:
            rd = ReactiveDict(factory())
        _register_transferable(ctx, key, rd)
        return rd

    warnings.warn(
        "use_reactive_dict() called outside component setup; dict will not be transferred",
        UserWarning,
        stacklevel=2,
    )
    return ReactiveDict(factory())


def use_counter(initial: int = 0) -> tuple[Any, Callable[[], None], Callable[[], None]]:
    count: Signal[int] = Signal(initial)

    def increment() -> None:
        count.value += 1

    def decrement() -> None:
        count.value -= 1

    return count, increment, decrement
