from abc import abstractmethod
from functools import wraps
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    ParamSpec,
    Set,
    Type,
    TypeVar,
    cast,
    final,
)


V = TypeVar("V")
A = ParamSpec("A")
T = TypeVar("T")


def _instantiate(cls: Type[T]) -> T:
    return cls()


@_instantiate
class ReactiveStore:
    __instances: dict[int, "ReactiveBase[Any]"]
    __on_before_updating: dict[int, Callable[[Any], Any]]
    __on_after_updating: dict[int, Callable[[Any], Any]]
    __callback_ids: dict[int, Set[int]]
    __latest_callback_id: int
    __dependency: list["ReactiveBase[Any]"] | None

    def __init__(self) -> None:
        self.__instances = {}
        self.__on_before_updating = {}
        self.__on_after_updating = {}
        self.__callback_ids = {}
        self.__latest_instance_id = 0
        self.__latest_callback_id = 0
        self.__dependency = None

    def add_reactive_instance(self, reactive: "ReactiveBase[Any]"):
        self.__latest_instance_id += 1
        reactive.__reactive_id__ = self.__latest_instance_id
        self.__instances[reactive.__reactive_id__] = reactive
        self.__callback_ids[reactive.__reactive_id__] = set()

    def add_on_after_updating(
        self, reactive: "ReactiveBase[Any]", func: Callable[[Any], Any]
    ):
        self.__latest_callback_id += 1
        callback_id = self.__latest_callback_id
        self.__on_after_updating[callback_id] = func
        self.__callback_ids[reactive.__reactive_id__].add(callback_id)
        return callback_id

    def add_on_before_updating(
        self, reactive: "ReactiveBase[Any]", func: Callable[[Any], Any]
    ):
        self.__latest_callback_id += 1
        callback_id = self.__latest_callback_id
        self.__on_before_updating[callback_id] = func
        self.__callback_ids[reactive.__reactive_id__].add(callback_id)
        return callback_id

    def callback_after_updating(self, instance: "ReactiveBase[Any]", value: Any):
        for idx, func in tuple(self.__on_after_updating.items()):
            if idx in self.__callback_ids[instance.__reactive_id__]:
                func(value)

    def callback_before_updating(self, instance: "ReactiveBase[Any]", value: Any):
        for idx, func in tuple(self.__on_before_updating.items()):
            if idx in self.__callback_ids[instance.__reactive_id__]:
                func(value)

    def resister(self, reactive: "ReactiveBase[Any]"):
        if self.__dependency is not None:
            self.__dependency.append(reactive)

    def detect_dependency(
        self, func: Callable[[], V]
    ) -> tuple[V, list["ReactiveBase[Any]"]]:
        self.__dependency = []
        value = func()
        dependency = self.__dependency
        self.__dependency = None
        uniq_ids: set[int] = set()
        return value, [
            reactive
            for reactive in dependency
            if reactive.__reactive_id__ not in uniq_ids
            and not uniq_ids.add(reactive.__reactive_id__)
        ]

    def remove_callback(self, callback_id: int):
        if callback_id in self.__on_after_updating:
            del self.__on_after_updating[callback_id]
        elif callback_id in self.__on_before_updating:
            del self.__on_before_updating[callback_id]
        targeted_isntance_id: int | None = None
        for isntance_id in self.__callback_ids:
            if callback_id in self.__callback_ids[isntance_id]:
                targeted_isntance_id = isntance_id
                break
        if targeted_isntance_id is not None:
            self.__callback_ids[targeted_isntance_id].remove(callback_id)


# Reactives
class ReactiveBase(Generic[V]):
    _store: ClassVar = ReactiveStore
    _value: V
    __reactive_id__: int

    def __init__(self, init_value: V) -> None:
        self._value = init_value
        self._store.add_reactive_instance(self)

    @property
    @abstractmethod
    def value(self) -> V:
        ...

    @final
    def on_after_updating(self, func: Callable[[V], Any]):
        return self._store.add_on_after_updating(self, func)

    @final
    def on_before_updating(self, func: Callable[[V], Any]):
        return self._store.add_on_before_updating(self, func)

    @final
    @staticmethod
    def _change_event(reactive_obj_method: Callable[A, V]) -> Callable[A, V]:
        @wraps(reactive_obj_method)
        def method(*args: A.args, **kwargs: A.kwargs) -> V:
            instance = cast(ReactiveBase[V], args[0])
            ReactiveBase._store.callback_before_updating(instance, instance._value)
            ret = reactive_obj_method(*args, **kwargs)
            ReactiveBase._store.callback_after_updating(instance, ret)
            return ret

        return method

    @final
    @staticmethod
    def _get_evnet(reactive_obj_method: Callable[A, V]) -> Callable[A, V]:
        @wraps(reactive_obj_method)
        def method(*args: A.args, **kwargs: A.kwargs) -> V:
            ReactiveBase._store.resister(cast(ReactiveBase[V], args[0]))
            return reactive_obj_method(*args, **kwargs)

        return method


class Reactive(ReactiveBase[V]):
    @final
    @ReactiveBase._change_event
    def set_value(self, new_value: V) -> V:
        self._value = new_value
        return self._value

    @final
    @property
    @ReactiveBase._get_evnet
    def value(self) -> V:
        return self._value

    @final
    @value.setter
    def value(self, new_value: V):
        self.set_value(new_value)
