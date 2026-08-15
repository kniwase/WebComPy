from __future__ import annotations

from collections.abc import Callable, Coroutine, Iterable
from re import compile as re_compile
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    Generic,
    Literal,
    TypeAlias,
    TypeGuard,
    TypeVar,
    cast,
    get_args,
)

from webcompy.components._component import Component
from webcompy.components._css_utils import (
    _contains_top_level_ampersand,
    _insert_cid,
    _is_declaration_body_at_rule,
    _is_host_syntax,
    _is_keyframes_rule,
    _raise_nesting_unsupported,
    _reject_host_forms,
    _resolve_host_part,
    _scope_selector,
)
from webcompy.components._libs import (
    ComponentContext,
    ComponentTemplateResult,
    NodeGenerator,
    WebComPyComponentException,
    generate_id,
)
from webcompy.components._reactive_scoped_style import ReactiveScopedStyle
from webcompy.utils._casing import kebab_to_pascal, pascal_to_kebab

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp

T = TypeVar("T")


def _instantiate(cls: type[T]) -> T:
    return cls()


class ComponentStore:
    _components: dict[str, ComponentGenerator[Any]]
    _custom_element_names: dict[str, str]

    def __init__(self) -> None:
        self._components = {}
        self._custom_element_names = {}

    def add_component(self, name: str, component_generator: ComponentGenerator[Any]):
        if name in self._components:
            raise WebComPyComponentException(f"Duplicated Component Name: '{name}'")
        custom_element_name = component_generator.custom_element_name
        existing = self._custom_element_names.get(custom_element_name)
        if existing is not None and existing != name:
            raise WebComPyComponentException(
                f"Duplicated Custom Element Name: '{custom_element_name}' (components '{existing}' and '{name}')"
            )
        self._custom_element_names[custom_element_name] = name
        self._components[name] = component_generator

    @property
    def components(self) -> dict[str, ComponentGenerator[Any]]:
        return self._components


PropsType = TypeVar("PropsType")
FuncComponentDef: TypeAlias = (
    Callable[[ComponentContext[PropsType]], ComponentTemplateResult]
    | Callable[[ComponentContext[PropsType]], Coroutine[Any, Any, ComponentTemplateResult]]
)

StyleDeclaration: TypeAlias = str | dict[str, "StyleDeclaration"]
StyleDict: TypeAlias = dict[str, StyleDeclaration]

ComponentDisplay: TypeAlias = Literal[
    "contents",
    "block",
    "inline",
    "inline-block",
    "flex",
    "inline-flex",
    "grid",
    "inline-grid",
    "flow-root",
]

_VALID_DISPLAY_VALUES: Final = frozenset(get_args(ComponentDisplay))


def _is_component_display(value: str) -> TypeGuard[ComponentDisplay]:
    return value in _VALID_DISPLAY_VALUES


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


def _render_declaration_at_rule(selector: str, declaration: dict[str, StyleDeclaration]) -> str:
    props: dict[str, str] = {}
    nested: dict[str, dict[str, StyleDeclaration]] = {}
    for key, value in declaration.items():
        if isinstance(value, dict):
            nested[key] = cast("dict[str, StyleDeclaration]", value)
        elif isinstance(value, str):
            props[key] = value
    parts: list[str] = []
    if props:
        parts.append(f"{selector} {{ {_format_properties(props)} }}")
    for nested_selector, nested_declaration in nested.items():
        parts.append(_render_declaration_at_rule(nested_selector.strip(), nested_declaration))
    return " ".join(parts)


def _render_at_rule_inner(style_dict: StyleDict, cid: str, host_tag: str) -> list[str]:
    inner_parts: list[str] = []
    for inner_sel, inner_styles in style_dict.items():
        stripped_inner = inner_sel.strip()
        if _is_keyframes_rule(stripped_inner):
            key_parts: list[str] = []
            for k, v in cast("dict[str, StyleDeclaration]", inner_styles).items():
                key_parts.append(_generate_css_recursive(k.strip(), cast("dict[str, StyleDeclaration]", v)))
            inner_parts.append(f"{stripped_inner} {{ {' '.join(key_parts)} }}")
        elif _is_declaration_body_at_rule(stripped_inner):
            inner_parts.append(
                _render_declaration_at_rule(stripped_inner, cast("dict[str, StyleDeclaration]", inner_styles))
            )
        elif _classify_nested_key(stripped_inner) == "at-rule":
            nested_parts = _render_at_rule_inner(cast("StyleDict", inner_styles), cid, host_tag)
            inner_parts.append(f"{stripped_inner} {{ {' '.join(nested_parts)} }}")
        elif _classify_nested_key(stripped_inner) == "pseudo":
            resolved = _resolve_host_part(stripped_inner, host_tag)
            if _is_host_syntax(stripped_inner):
                scoped = _insert_cid(resolved, cid)
            else:
                scoped = f"*[webcompy-cid-{cid}]{stripped_inner}"
            inner_parts.append(_generate_css_recursive(scoped, cast("dict[str, StyleDeclaration]", inner_styles)))
        elif _classify_nested_key(stripped_inner) == "combinator":
            scoped_inner = _scope_selector(stripped_inner, cid, host_tag=host_tag)
            inner_parts.append(_generate_css_recursive(scoped_inner, cast("dict[str, StyleDeclaration]", inner_styles)))
    return inner_parts


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
            _reject_host_forms(nested_selector)
            combined = f"{selector}{nested_selector}"
            result += _generate_css_recursive(combined, cast("dict[str, StyleDeclaration]", nested_styles))
        else:
            if _contains_top_level_ampersand(nested_selector):
                _raise_nesting_unsupported(nested_selector)
            combined = f"{selector} {nested_selector}"
            result += _generate_css_recursive(combined, cast("dict[str, StyleDeclaration]", nested_styles))
    return result


def _render_scoped_style_css(
    style: dict[str, StyleDict],
    cid: str,
    host_tag: str,
    *,
    leading_rules: Iterable[str] = (),
) -> str:
    parts: list[str] = list(leading_rules)
    for selector, style_dict in style.items():
        stripped = selector.strip()
        if _is_keyframes_rule(stripped):
            inner_parts: list[str] = []
            for inner_sel, inner_styles in style_dict.items():
                inner_parts.append(
                    _generate_css_recursive(
                        inner_sel.strip(),
                        cast("dict[str, StyleDeclaration]", inner_styles),
                    )
                )
            parts.append(f"{stripped} {{ {' '.join(inner_parts)} }}")
        elif _is_declaration_body_at_rule(stripped):
            parts.append(_render_declaration_at_rule(stripped, cast("dict[str, StyleDeclaration]", style_dict)))
        elif _classify_nested_key(stripped) == "at-rule":
            inner_parts = _render_at_rule_inner(style_dict, cid, host_tag)
            parts.append(f"{stripped} {{ {' '.join(inner_parts)} }}")
        else:
            parts.append(_generate_css_recursive(selector, cast("dict[str, StyleDeclaration]", style_dict)))
    body = " ".join(parts)
    if not body.strip():
        return ""
    return f"@layer webcompy-scope {{ {body} }}"


class ComponentGenerator(Generic[PropsType]):
    _name: str
    _cid: str
    _style: dict[str, StyleDict]
    _registered: bool
    _registered_app: WebComPyApp | None
    _custom_element_name: str
    _display: ComponentDisplay | None
    _observed_attributes: tuple[str, ...]
    _observed_prop_keys: dict[str, str]

    def __init__(
        self,
        name: str,
        component_def: FuncComponentDef[PropsType],
        *,
        custom_element_name: str,
        observed_attributes: tuple[str, ...] = (),
        display: ComponentDisplay | None = None,
    ) -> None:
        self._style = {}
        self._reactive_styles: list[ReactiveScopedStyle] = []
        self._component_def = component_def
        self._name: str = name
        self._cid = generate_id(name)
        self._registered = False
        self._registered_app = None
        self._custom_element_name = custom_element_name
        self._display = display
        self._observed_attributes = observed_attributes
        self._observed_prop_keys: dict[str, str] = {attr: attr.replace("-", "_") for attr in observed_attributes}
        if not self._try_register():
            _unregistered_generators.append(self)

    @property
    def _id(self) -> str:
        return self._cid

    @property
    def custom_element_name(self) -> str:
        return self._custom_element_name

    @property
    def display(self) -> ComponentDisplay | None:
        return self._display

    @property
    def observed_attributes(self) -> tuple[str, ...]:
        return self._observed_attributes

    @property
    def observed_prop_keys(self) -> dict[str, str]:
        return self._observed_prop_keys

    @property
    def definition_key(self) -> str:
        ordered_attributes = ",".join(sorted(self._observed_attributes))
        return f"webcompy-v1:{self._custom_element_name}:{ordered_attributes}"

    def _try_register(self) -> bool:
        from webcompy.di import inject
        from webcompy.di._keys import _APP_KEY, _COMPONENT_STORE_KEY

        store = inject(_COMPONENT_STORE_KEY, default=None)
        if store is None:
            return False
        app = inject(_APP_KEY, default=None)
        if self._registered_app is not None and app is not None and self._registered_app is not app:
            return True
        if self._name not in store.components:
            store.add_component(self._name, self)
            self._inject_scoped_style_if_new()
        self._registered = True
        if app is not None:
            self._registered_app = app
        return True

    def _inject_scoped_style_if_new(self) -> None:
        from webcompy.di import inject
        from webcompy.utils import ENVIRONMENT

        if ENVIRONMENT != "pyscript":
            return
        css = self.scoped_style
        if not css:
            return
        cid = self._id
        from webcompy.ports._keys import DOM_PORT_KEY

        _dom = inject(DOM_PORT_KEY, default=None)
        if _dom is None:
            return
        if _dom.query_selector(f'style[data-webcompy-cid="{cid}"]'):
            return
        head_el = _dom.query_selector("head")
        if not head_el:
            return
        el = _dom.create_element("style")
        el.setAttribute("data-webcompy-cid", cid)
        el.textContent = css
        head_el.appendChild(el)

    def __call__(
        self,
        props: PropsType,
        *,
        slots: dict[str, NodeGenerator] | None = None,
    ):
        return Component(
            self._component_def,
            props,
            {**slots} if slots else {},
            generator=self,
        )

    @property
    def scoped_style(self) -> str:
        leading_rules: tuple[str, ...] = ()
        if self._display is not None:
            leading_rules = (f"{self._custom_element_name}[webcompy-cid-{self._id}] {{ display: {self._display}; }}",)
        return _render_scoped_style_css(
            self._style,
            self._id,
            host_tag=self._custom_element_name,
            leading_rules=leading_rules,
        )

    @scoped_style.setter
    def scoped_style(self, style: dict[str, StyleDict]):
        cid = self._id
        host_tag = self._custom_element_name
        style_items: list[tuple[str, dict[str, StyleDeclaration]]] = []
        for selector, declaration in style.items():
            if _classify_nested_key(selector.strip()) == "at-rule":
                processed_selector = selector.strip()
            else:
                stripped = selector.strip()
                processed_selector = _scope_selector(stripped, cid, host_tag=host_tag)
            style_items.append((processed_selector, _process_style_declaration(declaration)))
        self._style = dict(style_items)
        self._inject_scoped_style_if_new()


_CUSTOM_ELEMENT_NAME_RE = re_compile(r"^[a-z][a-z0-9._-]*$")

_RESERVED_CUSTOM_ELEMENT_NAMES = frozenset(
    {
        "annotation-xml",
        "color-profile",
        "font-face",
        "font-face-src",
        "font-face-uri",
        "font-face-format",
        "font-face-name",
        "missing-glyph",
    }
)


def _validate_custom_element_name(name: str) -> None:
    if not isinstance(name, str) or "-" not in name or _CUSTOM_ELEMENT_NAME_RE.fullmatch(name) is None:
        raise WebComPyComponentException(
            f"Invalid custom element name: {name!r}. Custom element names must be lowercase and contain a hyphen. "
            "Single-word component names cannot form a valid custom element name; "
            "rename the component to a multi-word name (e.g., 'App' -> 'TodoApp' -> 'todo-app')."
        )
    if name in _RESERVED_CUSTOM_ELEMENT_NAMES:
        raise WebComPyComponentException(
            f"Invalid custom element name: {name!r}. The name is reserved by the custom elements specification."
        )


def _normalize_observed_attributes(observed_attributes: Iterable[str]) -> tuple[str, ...]:
    if isinstance(observed_attributes, str):
        raise WebComPyComponentException(
            "observed_attributes must be an iterable of attribute name strings, not a single string"
        )
    seen: list[str] = []
    seen_set: set[str] = set()
    for raw in observed_attributes:
        if not isinstance(raw, str) or not raw:
            raise WebComPyComponentException("Observed attribute names must be non-empty strings")
        name = raw.lower()
        if name in seen_set:
            raise WebComPyComponentException(f"Duplicate observed attribute: '{name}'")
        if name.startswith("webcompy-"):
            raise WebComPyComponentException(f"Framework attribute cannot be observed: '{name}'")
        seen.append(name)
        seen_set.add(name)
    keys: set[str] = set()
    for name in seen:
        key = name.replace("-", "_")
        if key in keys:
            raise WebComPyComponentException(f"Observed attributes collide on prop key '{key}': '{name}'")
        keys.add(key)
    return tuple(seen)


def _create_generator(
    setup: FuncComponentDef[PropsType],
    custom_element_name: str,
    observed_attributes: tuple[str, ...],
    display: ComponentDisplay | None,
) -> ComponentGenerator[PropsType]:
    setup.__webcompy_component_definition__ = True
    return ComponentGenerator(
        setup.__name__,
        setup,
        custom_element_name=custom_element_name,
        observed_attributes=observed_attributes,
        display=display,
    )


def define_component(
    name: str,
    *,
    observed_attributes: Iterable[str] = (),
    display: ComponentDisplay | None = None,
) -> Callable[[FuncComponentDef[PropsType]], ComponentGenerator[PropsType]]:
    _validate_custom_element_name(name)
    normalized = _normalize_observed_attributes(observed_attributes)
    if display is not None and (not isinstance(display, str) or not _is_component_display(display)):
        valid = ", ".join(get_args(ComponentDisplay))
        raise WebComPyComponentException(f"Invalid display value: {display!r}. Valid values: {valid}")

    def _decorator(component_def: FuncComponentDef[PropsType]) -> ComponentGenerator[PropsType]:
        expected_name = kebab_to_pascal(name)
        if component_def.__name__ != expected_name:
            derived = pascal_to_kebab(component_def.__name__)
            message = (
                f"Component name mismatch: '{name}' resolves to '{expected_name}' "
                f"but the setup function is named '{component_def.__name__}'. "
                f"Rename the function to '{expected_name}'"
            )
            try:
                _validate_custom_element_name(derived)
            except WebComPyComponentException:
                derived = None
            if derived is not None and kebab_to_pascal(derived) == component_def.__name__:
                message += f' or use @define_component("{derived}").'
            else:
                message += "."
            raise WebComPyComponentException(message)
        return _create_generator(component_def, name, normalized, display)

    return _decorator


def _register_deferred_components() -> None:
    for gen in _unregistered_generators:
        gen._try_register()
