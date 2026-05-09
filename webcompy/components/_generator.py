from __future__ import annotations

from collections.abc import Callable
from re import compile as re_compile
from typing import (
    Any,
    Final,
    Generic,
    TypeAlias,
    TypeVar,
    cast,
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

StyleDeclaration: TypeAlias = str | dict[str, "StyleDeclaration"]
StyleDict: TypeAlias = dict[str, StyleDeclaration]


_unregistered_generators: list[ComponentGenerator[Any]] = []


def _format_properties(props: dict[str, str]) -> str:
    return " ".join(f"{name}: {value};" for name, value in props.items())


def _process_style_declaration(declaration: dict[str, StyleDeclaration]) -> dict[str, StyleDeclaration]:
    result: dict[str, StyleDeclaration] = {}
    for key, value in declaration.items():
        if isinstance(value, dict):
            result[key] = _process_style_declaration(value)
        elif isinstance(value, str):
            result[key] = value.strip().rstrip(";").rstrip()
        else:
            result[key] = value
    return result


def _generate_css_recursive(selector: str, style_dict: dict[str, StyleDeclaration]) -> str:
    result = ""
    props: dict[str, str] = {}
    nested: dict[str, StyleDeclaration] = {}
    for key, value in style_dict.items():
        if isinstance(value, dict):
            nested[key] = value
        elif isinstance(value, str):
            props[key] = value
    if props:
        result += f"{selector} {{ {_format_properties(props)} }}"
    for nested_selector, nested_styles in nested.items():
        combined = f"{selector} {nested_selector}"
        result += _generate_css_recursive(combined, cast("dict[str, StyleDeclaration]", nested_styles))
    return result


class ComponentGenerator(Generic[PropsType]):
    _name: str
    _id: str
    _style: dict[str, StyleDict]
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
            _generate_css_recursive(selector, cast("dict[str, StyleDeclaration]", style_dict))
            for selector, style_dict in style.items()
        )

    @scoped_style.setter
    def scoped_style(self, style: dict[str, StyleDict]):
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
                (_process_style_declaration(declaration) for declaration in style.values()),
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
