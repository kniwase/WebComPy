from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Coroutine
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    Protocol,
    TypeAlias,
    TypedDict,
    TypeVar,
    final,
)

from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.exception import WebComPyException


class WebComPyComponentException(WebComPyException):
    pass


if TYPE_CHECKING:
    from webcompy.components._generator import ComponentGenerator
    from webcompy.components._reactive_scoped_style import ReactiveScopedStyle


NodeGenerator: TypeAlias = Callable[[], ElementChildren]
_Lifecyclehooks: TypeAlias = dict[
    Literal["on_before_rendering", "on_after_rendering", "on_before_destroy"],
    Callable[[], Any],
]

PropsType = TypeVar("PropsType", covariant=True)


@final
class Context(Generic[PropsType]):
    __slots: dict[str, NodeGenerator]
    __props: PropsType

    __on_before_rendering: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]] | None
    __on_after_rendering: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]] | None
    __on_before_destroy: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]] | None

    __title_getter: Callable[[], str]
    __meta_getter: Callable[[], dict[str, dict[str, str]]]
    __title_setter: Callable[[str], None]
    __meta_setter: Callable[[str, dict[str, str]], None]

    def __init__(
        self,
        props: PropsType,
        slots: dict[str, NodeGenerator],
        component_name: str,
        title_getter: Callable[[], str],
        meta_getter: Callable[[], dict[str, dict[str, str]]],
        title_setter: Callable[[str], None],
        meta_setter: Callable[[str, dict[str, str]], None],
        generator: ComponentGenerator[PropsType] | None = None,
    ) -> None:
        self.__props = props
        self.__slots = slots
        self._component_name = component_name
        self.__on_before_rendering = None
        self.__on_after_rendering = None
        self.__on_before_destroy = None
        self.__title_getter = title_getter
        self.__meta_getter = meta_getter
        self.__title_setter = title_setter
        self.__meta_setter = meta_setter
        self._generator = generator

    @property
    def props(self) -> PropsType:
        return self.__props

    def slots(
        self,
        name: str,
        fallback: NodeGenerator | None = None,
    ) -> ElementChildren:
        if name in self.__slots:
            return self.__slots[name]()
        elif fallback is not None:
            return fallback()
        else:
            logging.warning(f"Componet '{self._component_name}' is not given a slot named '{name}'")
            return None

    def on_before_rendering(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
        self.__on_before_rendering = func

    def on_after_rendering(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
        self.__on_after_rendering = func

    def on_before_destroy(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
        self.__on_before_destroy = func

    def get_title(self) -> str:
        return self.__title_getter()

    def get_meta(self) -> dict[str, dict[str, str]]:
        return self.__meta_getter()

    def set_title(self, title: str) -> None:
        self.__title_setter(title)

    def set_meta(self, key: str, attributes: dict[str, str]) -> None:
        self.__meta_setter(key, attributes)

    def provide(self, key: object, value: Any) -> None:
        from webcompy.di import provide as _provide

        _provide(key, value)

    def use_reactive_scoped_style(self, style: ReactiveScopedStyle) -> None:
        if self._generator is None:
            raise WebComPyException(
                "use_reactive_scoped_style() must be called from inside a @define_component "
                "setup function; the current Context has no associated ComponentGenerator"
            )
        from webcompy.components._reactive_scoped_style import ReactiveScopedStyle

        if not isinstance(style, ReactiveScopedStyle):
            raise WebComPyException(
                "use_reactive_scoped_style() expects a ReactiveScopedStyle instance; "
                "create one via reactive_scoped_style(func) before passing it"
            )

        is_first_use = style not in self._generator._reactive_styles
        if is_first_use:
            style._bind(self._generator._id)
            self._generator._reactive_styles.append(style)

        from webcompy.utils import ENVIRONMENT

        if ENVIRONMENT == "pyscript":
            from webcompy.components._hooks import on_before_destroy
            from webcompy.di import inject
            from webcompy.ports._keys import DOM_PORT_KEY
            from webcompy.signal._graph import consumer_destroy

            def _release_one_ref() -> None:
                style.decrement_ref()
                if style.ref_count == 0 and style.subscription is not None:
                    consumer_destroy(style.subscription)
                    style.set_subscription(None)

            on_before_destroy(_release_one_ref)

            if is_first_use:
                idx = len(self._generator._reactive_styles) - 1
                attr_value = f"{self._generator._id}-{idx}"
                css_computed = style._css_computed
                if css_computed is None:
                    raise WebComPyException("ReactiveScopedStyle is not bound; _bind() should have been called")

                def _update_text_content(v: str, _attr: str = attr_value) -> None:
                    _dom = inject(DOM_PORT_KEY)
                    el = _dom.query_selector(f'style[data-webcompy-cid-rx="{_attr}"]')
                    if el is not None:
                        el.textContent = v

                subscription = css_computed.on_after_updating(_update_text_content)
                style.set_subscription(subscription)

            style.increment_ref()

    def remove_reactive_scoped_style(self, style: ReactiveScopedStyle) -> None:
        """Remove a previously-registered reactive scoped style.

        The style is removed from the generator's ``_reactive_styles`` list
        and its reference count is decremented. If the reference count
        reaches zero (no other instance is using the style), the DOM
        subscription is disposed and will no longer fire on signal changes.

        Note: any ``<style data-webcompy-cid-rx="...">`` element that was
        already emitted to the DOM is left in place. The next full
        head-element render pass is responsible for reconciling (removing)
        elements whose corresponding style has been removed.
        """
        if self._generator is None:
            raise WebComPyException(
                "remove_reactive_scoped_style() must be called from inside a @define_component "
                "setup function; the current Context has no associated ComponentGenerator"
            )
        from webcompy.components._reactive_scoped_style import ReactiveScopedStyle

        if not isinstance(style, ReactiveScopedStyle):
            raise WebComPyException(
                "remove_reactive_scoped_style() expects a ReactiveScopedStyle instance; "
                "create one via reactive_scoped_style(func) before passing it"
            )

        if style not in self._generator._reactive_styles:
            return

        style.mark_removed()
        self._generator._reactive_styles.remove(style)
        style.decrement_ref()
        if style.ref_count == 0 and style.subscription is not None:
            from webcompy.signal._graph import consumer_destroy

            consumer_destroy(style.subscription)
            style.set_subscription(None)

    def __get_lifecyclehooks__(self) -> _Lifecyclehooks:
        hooks: _Lifecyclehooks = {}
        if self.__on_before_rendering:
            hooks["on_before_rendering"] = self.__on_before_rendering
        if self.__on_after_rendering:
            hooks["on_after_rendering"] = self.__on_after_rendering
        if self.__on_before_destroy:
            hooks["on_before_destroy"] = self.__on_before_destroy
        return hooks


class ComponentContext(Protocol[PropsType]):
    @property
    def props(self) -> PropsType: ...

    def slots(
        self,
        name: str,
        fallback: NodeGenerator | None = None,
    ) -> ElementChildren: ...

    def on_before_rendering(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None: ...

    def on_after_rendering(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None: ...

    def on_before_destroy(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None: ...

    def get_title(self) -> str: ...

    def get_meta(self) -> dict[str, dict[str, str]]: ...

    def set_title(self, title: str) -> None: ...

    def set_meta(self, key: str, attributes: dict[str, str]) -> None: ...

    def provide(self, key: object, value: Any) -> None: ...

    def use_reactive_scoped_style(self, style: ReactiveScopedStyle) -> None: ...

    def remove_reactive_scoped_style(self, style: ReactiveScopedStyle) -> None: ...


@final
class ComponentProperty(TypedDict):
    component_id: str
    component_name: str
    template: ElementChildren
    on_before_rendering: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
    on_after_rendering: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
    on_before_destroy: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]


def generate_id(component_name: str) -> str:
    return hashlib.md5(component_name.encode()).hexdigest()
