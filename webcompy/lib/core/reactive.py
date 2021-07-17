from typing import (Any, Callable, Dict, Optional, TypeVar, Generic, Union, cast)
from inspect import signature


T = TypeVar('T')


class Reactive(Generic[T]):
    def __init__(self, value: T) -> None:
        self.__value: T = value
        self.__getter_callbacks: Dict[
            str,
            Union[
                Callable[[Reactive[T], T], Any],
                Callable[[], Any]]
        ] = {}
        self.__setter_callbacks: Dict[
            str,
            Union[
                Callable[[Reactive[T], T, T], Any],
                Callable[[], Any]]
        ] = {}

    @property
    def value(self) -> T:
        for callback in self.__getter_callbacks.values():
            params = signature(callback).parameters
            if len(params):
                callback = cast(Callable[[Reactive[T], T], Any], callback)
                callback(self, self.__value)
            else:
                callback = cast(Callable[[], Any], callback)
                callback()
        return self.__value

    def __str__(self) -> str:
        for callback in self.__getter_callbacks.values():
            params = signature(callback).parameters
            if len(params):
                callback = cast(Callable[[Reactive[T], T], Any], callback)
                callback(self, self.__value)
            else:
                callback = cast(Callable[[], Any], callback)
                callback()
        return self.__value.__str__()

    @value.setter
    def value(self, value: T):
        old_value = self.__value
        self.__value: T = value
        for callback in self.__setter_callbacks.values():
            params = signature(callback).parameters
            if len(params):
                callback = cast(Callable[[Reactive[T], T, T], Any], callback)
                callback(self, old_value, self.__value)
            else:
                callback = cast(Callable[[], Any], callback)
                callback()

    @property
    def getter_actions(self):
        return self.__getter_callbacks

    @property
    def setter_actions(self):
        return self.__setter_callbacks


def reactive_text_evaluater(
    stat: str,
    globals: Dict[str, Any],
    locals: Optional[Dict[str, Any]] = {}
):
    value = eval(stat, globals, locals)
    if isinstance(value, str):
        return value
    elif hasattr(value, '__str__'):
        return str(value)
    else:
        return repr(value)


def reactive_prop_evaluater(
    stat: str,
    globals: Dict[str, Any],
    locals: Optional[Dict[str, Any]] = {}
):
    value = eval(stat, globals, locals)
    if isinstance(value, str):
        return value
    elif isinstance(value, bool):
        return 'true' if value else 'false'
    elif value is None:
        return None
    else:
        return value
