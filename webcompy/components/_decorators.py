from collections.abc import Callable
from functools import wraps
from typing import Any

from webcompy.elements.types._element import Element


def component_template(method: Callable[[Any], Element]):
    @wraps(method)
    def inner(self: Any) -> Element:
        return method(self)

    inner.__webcompy_component_class_property__ = "template"  # type: ignore[attr-defined]
    return inner


def on_before_rendering(method: Callable[[Any], None]):
    @wraps(method)
    def inner(self: Any):
        method(self)

    inner.__webcompy_component_class_property__ = "on_before_rendering"  # type: ignore[attr-defined]
    return inner


def on_after_rendering(method: Callable[[Any], None]):
    @wraps(method)
    def inner(self: Any):
        method(self)

    inner.__webcompy_component_class_property__ = "on_after_rendering"  # type: ignore[attr-defined]
    return inner


def on_before_destroy(method: Callable[[Any], None]):
    @wraps(method)
    def inner(self: Any):
        method(self)

    inner.__webcompy_component_class_property__ = "on_before_destroy"  # type: ignore[attr-defined]
    return inner
