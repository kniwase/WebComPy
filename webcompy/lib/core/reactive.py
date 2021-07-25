from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    TypeVar,
    Generic,
    final)


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

    def set_getter_action(self, name: str, action: Callable[[T], Any]):
        self.__getter_callbacks[name] = action

    def set_setter_action(self, name: str, action: Callable[[T, T], Any]):
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


class DefaultFactory:
    def __init__(self, factory: Callable[[], Any]) -> None:
        self.__factory__ = factory


def default_factory(factory: Callable[[], Any]) -> Any:
    return DefaultFactory(factory)


class ReactiveData:
    @final
    def __init__(self) -> None:
        self.__reactive_data_fields: Dict[str, Reactive[Any]] = {}
        self.__reactive_data_default_values = self.__get_default_values()

        for name, value in self.__reactive_data_default_values.items():
            self.__reactive_data_fields[name] = Reactive(value)
            if not hasattr(self.__class__, name) or \
                    not isinstance(getattr(self.__class__, name), property):
                setattr(
                    self.__class__,
                    name,
                    property(
                        self.__getter_factory(name),
                        self.__setter_factory(name)
                    )
                )

    @property
    @final
    def field_names(self):
        return self.__reactive_data_fields.keys()

    @final
    def as_dict(self):
        return {name: getattr(self, name) for name in self.field_names}

    def set_field_getter_action(
        self,
        field_name: str,
        action_name: str,
        action: Callable[[Any], Any]
    ):
        field = self.__reactive_data_fields[field_name]
        field.set_getter_action(action_name, action)

    def set_field_setter_action(
        self,
        field_name: str,
        action_name: str,
        action: Callable[[Any, Any], Any]
    ):
        field = self.__reactive_data_fields[field_name]
        field.set_setter_action(action_name, action)

    def remove_field_getter_action(
        self,
        field_name: str,
        action_name: str
    ):
        field = self.__reactive_data_fields[field_name]
        field.remove_getter_action(action_name)

    def remove_field_setter_action(
        self,
        field_name: str,
        action_name: str
    ):
        field = self.__reactive_data_fields[field_name]
        field.remove_setter_action(action_name)

    def get_field_getter_actions(self, field_name: str):
        field = self.__reactive_data_fields[field_name]
        return field.get_getter_actions()

    def get_field_setter_actions(self, field_name: str):
        field = self.__reactive_data_fields[field_name]
        return field.get_setter_actions()

    def __get_default_values(self):
        default_values: Dict[str, Optional[Any]] = {}
        field_names = set(
            name
            for name in self.__class__.__annotations__.keys()
            if not name.startswith('_')
        ).union(
            name
            for name in dir(self.__class__)
            if name not in dir(ReactiveData)
        )
        for name in field_names:
            if name.startswith('_'):
                continue
            if hasattr(self.__class__, name):
                value = getattr(self.__class__, name)
                if isinstance(value, DefaultFactory):
                    value = value.__factory__()
                default_values[name] = value
            else:
                default_values[name] = None
        return default_values

    def __getter_factory(self, name: str):
        reactive_data_fields = self.__reactive_data_fields

        def getter(_: Any):
            value = reactive_data_fields[name].value
            return value

        return getter

    def __setter_factory(self, name: str):
        reactive_data_fields = self.__reactive_data_fields

        def setter(_: Any, value: Any):
            reactive_data_fields[name].value = value

        return setter
