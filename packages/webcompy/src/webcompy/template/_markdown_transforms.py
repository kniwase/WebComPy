"""Post-render transforms applied to Markdown element trees."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any, TypeAlias

from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._element import Element
from webcompy.elements.types._text import TextElement
from webcompy.template._markdown_document import HeadingInfo
from webcompy.ui.code_block import CodeBlock

_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_WHITESPACE_RUN_RE = re.compile(r"\s+")
_LANGUAGE_CLASS_RE = re.compile(r"(?:^|\s)language-([^\s]+)")

Visitor: TypeAlias = Callable[[Any, list[Any], int], Any | None]


def _child_lists(element: Any) -> list[list[Any]]:
    lists: list[list[Any]] = []
    children = getattr(element, "_children", None)
    if isinstance(children, list):
        lists.append(children)
    pending = getattr(element, "_pending_children", None)
    if isinstance(pending, list):
        lists.append(pending)
    return lists


def _walk_elements(roots: list[Any], visit: Visitor) -> None:
    for i in range(len(roots)):
        child = roots[i]
        replacement = visit(child, roots, i)
        if replacement is not None:
            replacement._parent = getattr(child, "_parent", None)
            replacement._node_idx = getattr(child, "_node_idx", 0)
            roots[i] = replacement
            continue
        for lst in _child_lists(child):
            _walk_elements(lst, visit)


def _resolve_text(element: Any) -> str:
    if isinstance(element, TextElement):
        return element._get_text()
    parts: list[str] = []
    for lst in _child_lists(element):
        for child in lst:
            parts.append(_resolve_text(child))
    return "".join(parts)


def slugify(text: str) -> str:
    slug = _WHITESPACE_RUN_RE.sub("-", text.lower())
    return "".join(ch for ch in slug if ch.isalnum() or ch == "-")


class _SlugDeduplicator:
    def __init__(self) -> None:
        self._taken: set[str] = set()
        self._next: dict[str, int] = {}

    def assign(self, base: str) -> str:
        candidate = base
        n = self._next.get(base, 1)
        while candidate in self._taken:
            n += 1
            candidate = f"{base}-{n}"
        self._next[base] = n
        self._taken.add(candidate)
        return candidate

    def reserve(self, slug: str) -> None:
        self._taken.add(slug)


def _heading_id_visit_factory(dedupe: _SlugDeduplicator) -> Visitor:
    def visit(child: Any, lst: list[Any], i: int) -> Any | None:
        if isinstance(child, Element) and child._tag_name in _HEADING_TAGS:
            existing = child._attrs.get("id")
            if isinstance(existing, str):
                dedupe.reserve(existing)
            else:
                child._attrs["id"] = dedupe.assign(slugify(_resolve_text(child)))
        return None

    return visit


def _collect_headings_visit_factory(
    dedupe: _SlugDeduplicator,
    result: list[HeadingInfo],
    *,
    heading_ids: bool = True,
) -> Visitor:
    def visit(child: Any, lst: list[Any], i: int) -> Any | None:
        if isinstance(child, Element) and child._tag_name in _HEADING_TAGS:
            text = _resolve_text(child)
            existing = child._attrs.get("id")
            if isinstance(existing, str):
                dedupe.reserve(existing)
                heading_id = existing
            elif heading_ids:
                heading_id = dedupe.assign(slugify(text))
                child._attrs["id"] = heading_id
            else:
                heading_id = ""
            result.append(HeadingInfo(level=int(child._tag_name[1]), text=text, id=heading_id))
        return None

    return visit


def _code_block_visit() -> Visitor:
    def visit(child: Any, lst: list[Any], i: int) -> Any | None:
        if not isinstance(child, Element) or child._tag_name != "pre":
            return None
        significant = [c for c in child._children if not (isinstance(c, TextElement) and not c._get_text().strip())]
        if len(significant) != 1:
            return None
        code = significant[0]
        if not isinstance(code, Element) or code._tag_name != "code":
            return None
        class_attr = code._attrs.get("class")
        if not isinstance(class_attr, str):
            return None
        m = _LANGUAGE_CLASS_RE.search(class_attr)
        if m is None:
            return None
        return CodeBlock({"code": _resolve_text(code), "lang": m.group(1)})

    return visit


def _class_map_visit_factory(classes: Mapping[str, str]) -> Visitor:
    normalized = {tag.lower(): cls for tag, cls in classes.items()}

    def visit(child: Any, lst: list[Any], i: int) -> Any | None:
        if isinstance(child, Element) and child._tag_name in normalized:
            mapped = normalized[child._tag_name]
            existing = child._attrs.get("class")
            if existing is None:
                child._attrs["class"] = mapped
            elif isinstance(existing, str):
                child._attrs["class"] = f"{existing} {mapped}"
        return None

    return visit


def apply_heading_ids(root: ElementAbstract) -> None:
    """Inject slug ids into every heading element in the tree.

    Existing ``id`` attributes are reserved for deduplication and left
    unchanged.
    """
    _walk_elements([root], _heading_id_visit_factory(_SlugDeduplicator()))


def collect_headings(root: ElementAbstract, *, heading_ids: bool = True) -> tuple[HeadingInfo, ...]:
    """Collect headings in document order, injecting missing ids.

    When ``heading_ids`` is ``True`` (default), ids are guaranteed to match
    the ``id`` attributes present in the tree: headings lacking an id receive
    the same slug the id transform would assign. When ``False``, no ids are
    injected and headings without an existing ``id`` attribute yield an empty
    ``id`` in the resulting ``HeadingInfo``.
    """
    dedupe = _SlugDeduplicator()
    result: list[HeadingInfo] = []
    _walk_elements([root], _collect_headings_visit_factory(dedupe, result, heading_ids=heading_ids))
    return tuple(result)


def replace_code_blocks(root: ElementAbstract) -> None:
    """Replace ``<pre><code class="language-*">`` subtrees with CodeBlock.

    The root element itself is not replaced; use ``render_markdown`` with
    ``code_blocks=True`` for full coverage of root-level fenced blocks.
    """
    _walk_elements([root], _code_block_visit())


def apply_class_map(root: ElementAbstract, classes: Mapping[str, str]) -> None:
    """Merge tag -> CSS class mappings into matching elements additively."""
    _walk_elements([root], _class_map_visit_factory(classes))


def apply_heading_ids_to_roots(roots: list[ElementAbstract]) -> None:
    _walk_elements(roots, _heading_id_visit_factory(_SlugDeduplicator()))


def replace_code_blocks_in_roots(roots: list[ElementAbstract]) -> None:
    _walk_elements(roots, _code_block_visit())


def apply_class_map_to_roots(roots: list[ElementAbstract], classes: Mapping[str, str]) -> None:
    _walk_elements(roots, _class_map_visit_factory(classes))
