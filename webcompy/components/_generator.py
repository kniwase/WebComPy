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


def _classify_nested_key(key: str) -> str:
    if key.startswith("@"):
        return "at-rule"
    elif key.startswith(":"):
        return "pseudo"
    else:
        return "combinator"


def _format_properties(props: dict[str, str]) -> str:
    return " ".join(f"{name}: {value};" for name, value in props.items())


def _scope_combinator_selector(selector: str, cid: str) -> str:
    parts = _combinator_pattern.split(selector)
    combinators = [*_combinator_pattern.findall(selector), ""]
    scoped_parts: list[str] = []
    for i, (s, c) in enumerate(zip(parts, combinators, strict=True)):
        if not s and i == 0:
            scoped_parts.append(f"*[webcompy-cid-{cid}]{c}")
        elif s:
            scoped_parts.append(f"{s}[webcompy-cid-{cid}]{c}")
        else:
            scoped_parts.append(c)
    return "".join(scoped_parts)


def _process_style_declaration(declaration: dict[str, StyleDeclaration]) -> dict[str, StyleDeclaration]:
    result: dict[str, StyleDeclaration] = {}
    for key, value in declaration.items():
        if isinstance(value, dict):
            result[key] = _process_style_declaration(value)
        elif isinstance(value, str):
            result[key] = value.strip().rstrip(";").rstrip()
        else:
            raise TypeError(
                f"Invalid style value type for key '{key}': expected str or dict, got {type(value).__name__}"
            )
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
        key_type = _classify_nested_key(nested_selector)
        if key_type == "at-rule":
            inner_css = _generate_css_recursive(selector, cast("dict[str, StyleDeclaration]", nested_styles))
            result += f"{nested_selector} {{ {inner_css} }}"
        elif key_type == "pseudo":
            combined = f"{selector}{nested_selector}"
            result += _generate_css_recursive(combined, cast("dict[str, StyleDeclaration]", nested_styles))
        else:
            combined = f"{selector} {nested_selector}"
            result += _generate_css_recursive(combined, cast("dict[str, StyleDeclaration]", nested_styles))
    return result


class ComponentGenerator(Generic[PropsType]):
    _name: str
    _cid: str
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
        self._cid = generate_id(name)
        self._registered = False
        if not self._try_register():
            _unregistered_generators.append(self)

    @property
    def _id(self) -> str:
        return self._cid

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
        cid = self._id
        parts: list[str] = []
        for selector, style_dict in style.items():
            stripped = selector.strip()
            if stripped.startswith("@keyframes"):
                inner_parts: list[str] = []
                for inner_sel, inner_styles in style_dict.items():
                    inner_parts.append(
                        _generate_css_recursive(inner_sel.strip(), cast("dict[str, StyleDeclaration]", inner_styles))
                    )
                parts.append(f"{stripped} {{ {' '.join(inner_parts)} }}")
            elif _classify_nested_key(stripped) == "at-rule":
                inner_parts = self._process_at_rule_inner(style_dict, cid)
                parts.append(f"{stripped} {{ {' '.join(inner_parts)} }}")
            else:
                parts.append(_generate_css_recursive(selector, cast("dict[str, StyleDeclaration]", style_dict)))
        return " ".join(parts)

    def _process_at_rule_inner(self, style_dict: StyleDict, cid: str) -> list[str]:
        inner_parts: list[str] = []
        for inner_sel, inner_styles in style_dict.items():
            stripped_inner = inner_sel.strip()
            inner_type = _classify_nested_key(stripped_inner)
            if inner_type == "at-rule":
                if stripped_inner.startswith("@keyframes"):
                    key_parts: list[str] = []
                    for k, v in inner_styles.items():
                        key_parts.append(_generate_css_recursive(k.strip(), cast("dict[str, StyleDeclaration]", v)))
                    inner_parts.append(f"{stripped_inner} {{ {' '.join(key_parts)} }}")
                else:
                    nested_parts = self._process_at_rule_inner(cast("StyleDict", inner_styles), cid)
                    inner_parts.append(f"{stripped_inner} {{ {' '.join(nested_parts)} }}")
            elif inner_type == "pseudo":
                scoped = f"*[webcompy-cid-{cid}]{stripped_inner}"
                inner_parts.append(_generate_css_recursive(scoped, cast("dict[str, StyleDeclaration]", inner_styles)))
            elif inner_type == "combinator":
                scoped_inner = _scope_combinator_selector(stripped_inner, cid)
                inner_parts.append(
                    _generate_css_recursive(scoped_inner, cast("dict[str, StyleDeclaration]", inner_styles))
                )
            else:
                scoped_inner = f"{stripped_inner}[webcompy-cid-{cid}]"
                inner_parts.append(
                    _generate_css_recursive(scoped_inner, cast("dict[str, StyleDeclaration]", inner_styles))
                )
        return inner_parts

    @scoped_style.setter
    def scoped_style(self, style: dict[str, StyleDict]):
        cid = self._id
        style_items: list[tuple[str, dict[str, StyleDeclaration]]] = []
        for selector, declaration in style.items():
            if _classify_nested_key(selector.strip()) == "at-rule":
                processed_selector = selector.strip()
            else:
                stripped = selector.strip()
                processed_selector = "".join(
                    f"{s}[webcompy-cid-{cid}]{c}"
                    for s, c in zip(
                        _combinator_pattern.split(stripped),
                        [*_combinator_pattern.findall(stripped), ""],
                        strict=True,
                    )
                )
            style_items.append((processed_selector, _process_style_declaration(declaration)))
        self._style = dict(style_items)


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
