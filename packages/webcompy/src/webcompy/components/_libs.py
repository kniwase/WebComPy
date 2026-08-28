"""Shared component types: the context protocol, exceptions, and type aliases."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Coroutine
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    NotRequired,
    Protocol,
    TypeAlias,
    TypedDict,
    TypeVar,
    final,
)

from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.exception import WebComPyException


class WebComPyComponentException(WebComPyException):
    """Error raised for invalid component definitions or usage."""

    pass


if TYPE_CHECKING:
    from webcompy.components._generator import ComponentGenerator
    from webcompy.components._reactive_scoped_style import ReactiveScopedStyle
    from webcompy.signal import SignalBase


NodeGenerator: TypeAlias = Callable[[], ElementChildren]
ComponentTemplateResult: TypeAlias = ElementChildren | list[ElementChildren] | tuple[ElementChildren, ...]
_Lifecyclehooks: TypeAlias = dict[
    Literal[
        "on_before_rendering",
        "on_after_rendering",
        "on_before_destroy",
        "on_mounted",
        "on_unmounted",
    ],
    Callable[[], Any],
]

PropsType = TypeVar("PropsType", covariant=True)


@final
class Context(Generic[PropsType]):
    __slots: dict[str, NodeGenerator]
    __props: PropsType

    __on_before_rendering: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]] | None
    __on_after_rendering: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]] | None
    __on_before_destroy: list[Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]]
    __on_mounted: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]] | None
    __on_unmounted: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]] | None

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
        transfer_id: str | None = None,
    ) -> None:
        self.__props = props
        self.__slots = slots
        self._component_name = component_name
        self._transfer_id = transfer_id or generate_id(component_name)
        self.__on_before_rendering = None
        self.__on_after_rendering = None
        self.__on_before_destroy = []
        self.__on_mounted = None
        self.__on_unmounted = None
        self.__title_getter = title_getter
        self.__meta_getter = meta_getter
        self.__title_setter = title_setter
        self.__meta_setter = meta_setter
        self._generator = generator
        self._async_results: list = []
        self._transferable_signals: dict[str, SignalBase[Any]] = {}
        self._error_captured_hooks: list[Callable[[Exception], Any]] = []

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
        self.__on_before_destroy.append(func)

    def on_mounted(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
        self.__on_mounted = func

    def on_unmounted(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
        self.__on_unmounted = func

    def on_error_captured(self, func: Callable[[Exception], Any]) -> None:
        self._error_captured_hooks.append(func)

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
            style._bind(self._generator._id, host_tag=self._generator.custom_element_name)
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

            def _combined() -> None:
                for _hook in self.__on_before_destroy:
                    _hook()

            hooks["on_before_destroy"] = _combined
        if self.__on_mounted:
            hooks["on_mounted"] = self.__on_mounted
        if self.__on_unmounted:
            hooks["on_unmounted"] = self.__on_unmounted
        return hooks


class ComponentContext(Protocol[PropsType]):
    """Interface the component setup function receives.

    The framework passes an implementation of this protocol as the
    setup function's argument: it exposes props, named slots, lifecycle
    hook registration, document head helpers, DI provisioning, and
    reactive scoped style registration.

    Attributes:
        props: The props object passed to the component.

    """

    @property
    def props(self) -> PropsType:
        """Return the props object passed to the component.

        Returns:
            The component props.

        """
        ...

    def slots(
        self,
        name: str,
        fallback: NodeGenerator | None = None,
    ) -> ElementChildren:
        """Render the named slot contents.

        Args:
            name: Name of the slot to render.
            fallback: Contents rendered when the slot is not provided.

        Returns:
            The rendered slot children, or the fallback children.

        """
        ...

    def on_before_rendering(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
        """Register a hook invoked before the component renders.

        Args:
            func: Hook callback; may be a coroutine function.

        """
        ...

    def on_after_rendering(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
        """Register a hook invoked after the component renders.

        Args:
            func: Hook callback; may be a coroutine function.

        """
        ...

    def on_before_destroy(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
        """Register a hook invoked before the component is destroyed.

        Args:
            func: Hook callback; may be a coroutine function.

        """
        ...

    def on_mounted(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
        """Register a hook invoked when the component enters the DOM.

        Args:
            func: Hook callback; may be a coroutine function.

        """
        ...

    def on_unmounted(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
        """Register a hook invoked when the component leaves the DOM.

        Args:
            func: Hook callback; may be a coroutine function.

        """
        ...

    def on_error_captured(self, func: Callable[[Exception], Any]) -> None:
        """Register a hook invoked when a descendant error is captured.

        Args:
            func: Hook callback receiving the raised exception.

        """
        ...

    def get_title(self) -> str:
        """Return the current document title.

        Returns:
            The document title.

        """
        ...

    def get_meta(self) -> dict[str, dict[str, str]]:
        """Return the collected document head meta entries.

        Returns:
            Mapping of meta key to its attribute mapping.

        """
        ...

    def set_title(self, title: str) -> None:
        """Set the document title while this component exists.

        Args:
            title: New document title.

        """
        ...

    def set_meta(self, key: str, attributes: dict[str, str]) -> None:
        """Set a document head meta entry while this component exists.

        Args:
            key: Unique key of the meta entry.
            attributes: Mapping of attribute names to values.

        """
        ...

    def provide(self, key: object, value: Any) -> None:
        """Provide a dependency value in the component's DI scope.

        Args:
            key: Dependency key the value is registered under.
            value: Value to provide.

        """
        ...

    def use_reactive_scoped_style(self, style: ReactiveScopedStyle) -> None:
        """Register a reactive scoped style for this component.

        Args:
            style: Reactive scoped style created by
                ``reactive_scoped_style()``.

        """
        ...

    def remove_reactive_scoped_style(self, style: ReactiveScopedStyle) -> None:
        """Remove a previously registered reactive scoped style.

        Args:
            style: Reactive scoped style previously registered via
                ``use_reactive_scoped_style()``.

        """
        ...


@final
class ComponentProperty(TypedDict):
    """Bundle of a component instance's resolved setup results and hooks.

    Attributes:
        component_id: Stable identifier of the component instance.
        component_name: Registered name of the component.
        transfer_id: Optional stable id used for hydration value
            transfer; present when a custom transfer key is assigned.
        template: Rendered template result, or ``None`` before render.
        on_before_rendering: Hook invoked before the component renders.
        on_after_rendering: Hook invoked after the component renders.
        on_before_destroy: Hook invoked before the component is
            destroyed.
        on_mounted: Hook invoked when the component enters the DOM.
        on_unmounted: Hook invoked when the component leaves the DOM.

    """

    component_id: str
    component_name: str
    transfer_id: NotRequired[str]
    template: ComponentTemplateResult | None
    on_before_rendering: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
    on_after_rendering: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
    on_before_destroy: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
    on_mounted: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
    on_unmounted: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]


def generate_id(component_name: str) -> str:
    return hashlib.md5(component_name.encode()).hexdigest()
