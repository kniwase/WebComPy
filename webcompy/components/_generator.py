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


def _instantiate(cls: type[T]) -> T:
    return cls()


class ComponentStore:
    _components: dict[str, ComponentGenerator[Any]]

    def __init__(self) -> None:
        self._components = {}

    def add_component(self, name: str, component_generator: ComponentGenerator[Any]):
        if name in self._components:
            raise WebComPyComponentException(f"Duplicated Component Name: '{name}'")
        self._components[name] = component_generator

    @property
    def components(self) -> dict[str, ComponentGenerator[Any]]:
        return self._components


PropsType = TypeVar("PropsType")
FuncComponentDef: TypeAlias = Callable[[ComponentContext[PropsType]], ElementChildren]


_unregistered_generators: list[ComponentGenerator[Any]] = []


class ComponentGenerator(Generic[PropsType]):
    _name: str
    _id: str
    _style: dict[str, dict[str, str]]
    _registered: bool

    def __init__(
        self,
        name: str,
        component_def: FuncComponentDef[PropsType],
    ) -> None:
        self._style = {}
        self._component_def = component_def
        self._name: str = name
        self._id = generate_id(name)
        self._registered = False
        if not self._try_register():
            _unregistered_generators.append(self)

    def _try_register(self) -> bool:
        if self._registered:
            return True
        from webcompy.di import inject
        from webcompy.di._keys import _COMPONENT_STORE_KEY

        store = inject(_COMPONENT_STORE_KEY, default=None)
        if store is not None:
            store.add_component(self._name, self)
            self._registered = True
            return True
        return False

    def __call__(
        self,
        props: PropsType,
        *,
        slots: dict[str, NodeGenerator] | None = None,
    ):
        return Component(self._component_def, props, {**slots} if slots else {})

    @property
    def scoped_style(self) -> str:
        style = self._style
        return " ".join(
            f"{selector} {{ " + " ".join(f"{name}: {value};" for name, value in props.items()) + " }"
            for selector, props in style.items()
        )

    @scoped_style.setter
    def scoped_style(self, style: dict[str, dict[str, str]]):
        cid = self._id
        self._style = dict(
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


def _register_deferred_components() -> None:
    global _unregistered_generators
    remaining: list[ComponentGenerator[Any]] = []
    for gen in _unregistered_generators:
        if not gen._try_register():
            remaining.append(gen)
    _unregistered_generators = remaining
