from typing import Any, Callable, TypeVar
from webcompy.reactive._base import ReactiveBase
from webcompy.reactive._container import ReactiveReceivable


V = TypeVar("V")


class Computed(ReactiveBase[V]):
    _dependencies: list[ReactiveBase[Any]]
    _dependency_callback_ids: list[int]

    def __init__(
        self,
        func: Callable[[], V],
    ) -> None:
        self.__calc = func
        init_value, self._dependencies = self._store.detect_dependency(self.__calc)
        self._dependency_callback_ids = [
            reactive.on_after_updating(self._compute) for reactive in self._dependencies
        ]
        super().__init__(init_value)

    @property
    @ReactiveBase._get_evnet
    def value(self) -> V:
        return self._value

    @ReactiveBase._change_event
    def _compute(self, *_: Any) -> V:
        self._value = self.__calc()
        return self._value


def computed(func: Callable[[], V]) -> Computed[V]:
    return Computed(func)


def computed_property(method: Callable[[Any], V]) -> Computed[V]:
    name = method.__name__

    def getter(instance: Any) -> Computed[V]:
        if name not in instance.__dict__:
            _computed = Computed(lambda: method(instance))
            if isinstance(instance, ReactiveReceivable):
                instance.__set_reactive_member__(_computed)
            instance.__dict__[name] = _computed
        return instance.__dict__[name]

    return property(getter)  # type: ignore
