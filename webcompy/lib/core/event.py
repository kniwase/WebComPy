from typing import Any, Union, Callable, Coroutine, Dict
from operator import truth
from inspect import signature
from browser import aio
from .uniq_id import generate_uid


EventCallback = Union[Callable[[], Union[None, Coroutine[Any, Any, None]]],
                      Callable[[Any], Union[None, Coroutine[Any, Any, None]]]]


callback_repository: Dict[int, EventCallback] = {}
emit_arg_repository: Dict[int, Any] = {}


def get_callback_function(idx: Union[str, int]) -> EventCallback:
    return callback_repository.pop(int(idx))


def register_emitted_arg(arg: Any) -> int:
    idx = generate_uid(emit_arg_repository)
    emit_arg_repository[idx] = arg
    return idx


def get_emitted_arg(idx: int) -> Any:
    return emit_arg_repository.pop(idx)


def event_handler_wrapper(callback: Any) -> EventCallback:
    params = signature(callback).parameters
    has_arg = truth(params)

    def event_handler(ev: Any):
        is_webcompy_emit = hasattr(ev.detail,
                                   'webcompyEmittedArgument')
        if is_webcompy_emit:
            idx = ev.detail.webcompyEmittedArgument
            arg = get_emitted_arg(idx)
        else:
            arg = ev
        if has_arg:
            ret = callback(arg)
        else:
            ret = callback()
        if ret:
            aio.run(ret)

    return event_handler
