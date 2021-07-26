from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    TypeVar,
    Generic,
    cast,
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

    def remove_all_getter_actions(self):
        del self.__getter_callbacks
        self.__getter_callbacks = {}

    def remove_all_setter_actions(self):
        del self.__setter_callbacks
        self.__setter_callbacks = {}

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
    __reactive_data_fields: Dict[str, Reactive[Any]]
    __reactive_data_default_values: Dict[str, Optional[Any]]

    @final
    def __init__(self) -> None:
        self.__setup__(self.__get_default_values())

    def __setup__(self, fields: Dict[str, Optional[Any]]):
        self.__reactive_data_fields = {}
        self.__reactive_data_default_values = {}
        for name, value in fields.items():
            self.__reactive_data_default_values[name] = value
            if name not in self.__reactive_data_fields:
                self.__reactive_data_fields[name] = Reactive(value)
            else:
                self.__reactive_data_fields[name].value = value
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
        for name in tuple(self.__reactive_data_default_values.keys()):
            if name not in fields:
                del self.__reactive_data_default_values[name]
        for name in tuple(self.__reactive_data_fields.keys()):
            if name not in fields:
                del self.__reactive_data_fields[name]
        for name in dir(self.__class__):
            if name not in fields and \
                    isinstance(getattr(self.__class__, name), property):
                delattr(self.__class__, name)

    @final
    def get_field_value(self, field_name: str):
        value = self.__reactive_data_fields[field_name].value
        return value

    @final
    def set_field_value(self, field_name: str, value: Any):
        self.__reactive_data_fields[field_name].value = value

    def __getter_factory(self, field_name: str):
        def getter(self: Any):
            return self.get_field_value(field_name)
        return getter

    def __setter_factory(self, field_name: str):
        def setter(self: Any, value: Any):
            self.set_field_value(field_name, value)
        return setter

    @property
    @final
    def field_names(self):
        return self.__reactive_data_fields.keys()

    @final
    def as_dict(self):
        return {name: getattr(self, name) for name in self.field_names}

    @final
    def clone(self: T) -> T:
        new_data = cast(ReactiveData, self.__class__())
        new_data.__setup__(cast(Any, self).__reactive_data_default_values)
        return cast(T, new_data)

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

    def remove_all_field_getter_actions(self):
        for field_name in self.field_names:
            field = self.__reactive_data_fields[field_name]
            field.remove_all_getter_actions()

    def remove_all_field_setter_actions(self):
        for field_name in self.field_names:
            field = self.__reactive_data_fields[field_name]
            field.remove_all_setter_actions()

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
