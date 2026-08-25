"""Tag-name resolution between templates and the component registry."""

from __future__ import annotations

from enum import Enum

from webcompy.components._generator import ComponentStore
from webcompy.exception import WebComPyException
from webcompy.utils._casing import kebab_to_pascal, kebab_to_snake, pascal_to_kebab

__all__ = [
    "TagResolution",
    "kebab_to_pascal",
    "kebab_to_snake",
    "pascal_to_kebab",
    "resolve_tag",
]


class TagResolution(Enum):
    """Outcome of resolving a parsed tag name.

    Attributes:
        NEWLINE: Tag is ``<br>``; renders as a newline element.
        HTML: Tag names a built-in HTML element.
        COMPONENT: Tag names a registered component.

    """

    NEWLINE = "newline"
    HTML = "html"
    COMPONENT = "component"


def resolve_tag(tag: str, store: ComponentStore) -> tuple[TagResolution, str | None]:
    """Resolve a parsed tag name to either NEWLINE / HTML / COMPONENT.

    Returns ``(TagResolution, component_name_or_None)``. ``component_name`` is
    the registered name in ``ComponentStore`` when resolution is COMPONENT;
    for the other outcomes it is ``None``.

    Resolution rules:

    * ``"br"`` → NEWLINE (special-cased to skip ComponentStore lookup).
    * Tag containing at least one hyphen → kebab-to-Pascal conversion, then
      ComponentStore lookup. A missing match raises ``WebComPyException``
      because the user explicitly used a hyphenated component-like tag.
    * Tag with no hyphen → ComponentStore lookup using the tag name as-is.
      A missing match falls back to HTML element (lenient, since the tag is
      ambiguous and could be a future HTML custom element).

    Args:
        tag: Parsed tag name.
        store: Component registry used for COMPONENT resolution.

    Returns:
        Pair of the resolution kind and the registered component name when
        the resolution is COMPONENT, otherwise ``None``.

    Raises:
        WebComPyException: If a hyphenated tag does not match any registered
            component.

    """
    if tag == "br":
        return TagResolution.NEWLINE, None

    component_name = kebab_to_pascal(tag) if "-" in tag else tag

    if component_name in store.components:
        return TagResolution.COMPONENT, component_name

    if "-" in tag:
        available = sorted(store.components.keys())
        available_repr = repr(available)
        raise WebComPyException(
            f"Component '{component_name}' not found for tag <{tag}>. "
            f"Component tags require PascalCase component function names "
            f"(e.g., <{tag}> resolves to {component_name}). "
            f"If your component is defined with a different name, use the "
            f"Python API instead. Did you forget to import it? "
            f"Available: {available_repr}"
        )

    return TagResolution.HTML, None
