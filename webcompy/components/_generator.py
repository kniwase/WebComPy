from __future__ import annotations

from collections.abc import Callable
from re import compile as re_compile
from typing import (
    Any,
    Final,
    Generic,
    TypeAlias,
    TypeVar,
)

from webcompy.components._component import Component
from webcompy.components._libs import ComponentContext, NodeGenerator, WebComPyComponentException, generate_id
from webcompy.elements.typealias._element_property import ElementChildren

_camel_to_kebab_pattern: Final = re_compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")
_combinator_pattern: Final = re_compile(r"\s*,\s*|\s*>\s*|\s*\+\s*|\s*~[^=]\s*|\s* \s*")


T = TypeVar("T")


class _ComponentStoreImpl:
    __components: dict[str, Any]

    def __init__(self) -> None:
        self.__components = {}

    def add_component(self, name: str, component_generator: Any):
        if name in self.__components:
            raise WebComPyComponentException(f"Duplicated Component Name: '{name}'")
        self.__components[name] = component_generator

    @property
    def components(self) -> dict[str, Any]:
        return self.__components


_default_component_store: _ComponentStoreImpl | None = None


def _get_default_component_store() -> _ComponentStoreImpl:
    global _default_component_store
    if _default_component_store is None:
        _default_component_store = _ComponentStoreImpl()
    return _default_component_store


ComponentStore: _ComponentStoreImpl = _get_default_component_store()


PropsType = TypeVar("PropsType")
FuncComponentDef: TypeAlias = Callable[[ComponentContext[PropsType]], ElementChildren]


class ComponentGenerator(Generic[PropsType]):
    __name: str
    __id: str
    __style: dict[str, dict[str, str]]

    def __init__(
        self,
        name: str,
        component_def: FuncComponentDef[PropsType],
    ) -> None:
        self.__style = {}
        self.__component_def = component_def
        self.__name: str = name
        self.__id = generate_id(name)
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.di._scope import _active_di_scope

        scope = _active_di_scope.get(None)
        if scope is not None:
            try:
                store = scope.inject(_COMPONENT_STORE_KEY)
            except Exception:
                store = _get_default_component_store()
        else:
            store = _get_default_component_store()
        store.add_component(self.__name, self)

    def __call__(
        self,
        props: PropsType,
        *,
        slots: dict[str, NodeGenerator] | None = None,
    ):
        return Component(self.__component_def, props, {**slots} if slots else {})

    @property
    def scoped_style(self) -> str:
        style = self.__style
        return " ".join(
            f"{selector} {{ " + " ".join(f"{name}: {value};" for name, value in props.items()) + " }"
            for selector, props in style.items()
        )

    @scoped_style.setter
    def scoped_style(self, style: dict[str, dict[str, str]]):
        cid = self.__id
        self.__style = dict(
            zip(
                (
                    "".join(
                        f"{selector}[webcompy-cid-{cid}]{combinator}"
                        for selector, combinator in zip(
                            _combinator_pattern.split(selector),
                            [*_combinator_pattern.findall(selector), ""],
                            strict=True,
                        )
                    )
                    for selector in map(lambda s: s.strip(), style.keys())
                ),
                (
                    {prop: value.strip().rstrip(";").rstrip() for prop, value in declaration.items()}
                    for declaration in style.values()
                ),
                strict=True,
            )
        )


def define_component(
    setup: Callable[[ComponentContext[PropsType]], ElementChildren],
) -> ComponentGenerator[PropsType]:
    setup.__webcompy_component_definition__ = True
    return ComponentGenerator(setup.__name__, setup)
