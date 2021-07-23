from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    TypeVar,
    Generic)


T = TypeVar('T')


class Reactive(Generic[T]):
    def __init__(self, value: T) -> None:
        self.__value: T = value
        self.__getter_callbacks: Dict[str, Callable[[T], Any]] = {}
        self.__setter_callbacks: Dict[str, Callable[[T, T], Any]] = {}

    @property
    def value(self) -> T:
        for callback in self.__getter_callbacks.values():
            callback(self.__value)
        return self.__value

    @value.setter
    def value(self, value: T):
        old_value = self.__value
        self.__value: T = value
        for callback in self.__setter_callbacks.values():
            callback(old_value, self.__value)

    def add_getter_action(self, name: str, action: Callable[[T], Any]):
        self.__getter_callbacks[name] = action

    def add_setter_action(self, name: str, action: Callable[[T, T], Any]):
        self.__setter_callbacks[name] = action

    def remove_getter_action(self, name: str):
        del self.__getter_callbacks[name]

    def remove_setter_action(self, name: str):
        del self.__setter_callbacks[name]

    def get_getter_actions(self):
        return dict(self.__getter_callbacks.items())

    def get_setter_actions(self):
        return dict(self.__setter_callbacks.items())

    def clone(self):
        new: Reactive[T] = Reactive(self.__value)
        return new


def eval_reactive_text(
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


def eval_reactive_prop(
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
