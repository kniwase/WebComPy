from functools import wraps
from typing import Any, Callable
from webcompy.elements.types._element import Element


def component_template(method: Callable[[Any], Element]):
    @wraps(method)
    def inner(self: Any) -> Element:
        return method(self)

    setattr(inner, "__webcompy_component_class_property__", "template")
    return inner


def on_before_rendering(method: Callable[[Any], None]):
    @wraps(method)
    def inner(self: Any):
        method(self)

    setattr(
        inner,
        "__webcompy_component_class_property__",
        "on_before_rendering",
    )
    return inner


def on_after_rendering(method: Callable[[Any], None]):
    @wraps(method)
    def inner(self: Any):
        method(self)

    setattr(
        inner,
        "__webcompy_component_class_property__",
        "on_after_rendering",
    )
    return inner


def on_before_destroy(method: Callable[[Any], None]):
    @wraps(method)
    def inner(self: Any):
        method(self)

    setattr(inner, "__webcompy_component_class_property__", "on_before_destroy")
    return inner
