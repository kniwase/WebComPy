"""Read-only CSS selector resolution over the server virtual DOM.

Implements a documented selector subset for ``ServerDOMPort.query_selector``:
type selectors, class selectors (``.name``), ID selectors (``#id``), their
compounds (``div.a#b``), descendant combinators (whitespace), child
combinators (``>``), and comma-separated groups. Any other syntax — attribute
selectors, pseudo-classes, wildcards, quotes — raises :class:`ValueError`.

Matching follows HTML document semantics: type selectors are matched ASCII
case-insensitively, while class and ID values are matched case-sensitively on
both the selector and the attribute side.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from webcompy.ports._dom import DOMNode

_DESCENDANT = " "
_CHILD = ">"

_IDENTIFIER_START_RE = re.compile(r"[-A-Za-z_]")
_IDENTIFIER_BODY_RE = re.compile(r"[-A-Za-z0-9_]*")


@dataclass(frozen=True)
class _SimpleSelector:
    """One compound term: optional tag plus class and id requirements."""

    tag: str | None
    classes: frozenset[str]
    ids: frozenset[str]


@dataclass(frozen=True)
class _SelectorChain:
    """A single compound sequence joined by combinators.

    Each part holds a simple selector and the combinator linking it to the
    *following* part (empty string on the last part).
    """

    parts: tuple[tuple[_SimpleSelector, str], ...]


def parse_selector(selector: str) -> list[_SelectorChain]:
    """Parse ``selector`` into its comma-separated chains.

    Type selectors are normalized to lower case; class and ID values are
    kept verbatim so matching stays case-sensitive, mirroring HTML document
    semantics.

    Args:
        selector: Selector text from the supported subset.

    Returns:
        Parsed chains in source order.

    Raises:
        ValueError: When the selector uses unsupported syntax or is empty.

    """
    text = selector.strip()
    if not text:
        raise ValueError(f"Empty selector: {selector!r}")
    chains: list[_SelectorChain] = []
    position = 0
    while True:
        parts, position = _parse_chain(text, position)
        chains.append(_SelectorChain(parts))
        if position >= len(text):
            return chains
        if text[position] != ",":
            raise ValueError(f"Invalid selector syntax: {selector!r}")
        position += 1
        position = _skip_whitespace(text, position)
        if position >= len(text):
            raise ValueError(f"Invalid selector syntax: {selector!r}")


def resolve_first(root: DOMNode, selector: str) -> DOMNode | None:
    """Return the first matching node in depth-first document order.

    Type selectors match ASCII case-insensitively; class and ID values
    match case-sensitively.

    Args:
        root: Node whose subtree (including itself) is searched.
        selector: Selector text from the supported subset.

    Returns:
        First matching element node, or ``None`` when nothing matches.

    Raises:
        ValueError: When the selector uses unsupported syntax.

    """
    try:
        parsed = parse_selector(selector)
    except ValueError:
        raise
    return resolve_parsed(root, parsed)


def resolve_parsed(root: DOMNode, chains: list[_SelectorChain]) -> DOMNode | None:
    """Return the first node matching pre-parsed ``chains``.

    Args:
        root: Node whose subtree (including itself) is searched.
        chains: Parsed selector chains from :func:`parse_selector`.

    Returns:
        First matching element node, or ``None`` when nothing matches.

    """
    stack: list[DOMNode] = [root]
    while stack:
        node = stack.pop()
        if node.nodeType != 1:
            continue
        if any(_matches_chain(node, chain, root) for chain in chains):
            return node
        children = node.childNodes
        for index in range(children.length - 1, -1, -1):
            stack.append(children[index])
    return None


def _parse_chain(text: str, start: int) -> tuple[tuple[tuple[_SimpleSelector, str], ...], int]:
    parts: list[tuple[_SimpleSelector, str]] = []
    position = _skip_whitespace(text, start)
    simple, position = _parse_compound(text, position)
    parts.append((simple, ""))
    while True:
        position = _skip_whitespace(text, position)
        if position >= len(text) or text[position] == ",":
            return tuple(parts), position
        combinator = _DESCENDANT
        if text[position] == ">":
            combinator = _CHILD
            position = _skip_whitespace(text, position + 1)
        following, position = _parse_compound(text, position)
        latest = parts[-1][0]
        parts[-1] = (latest, combinator)
        parts.append((following, ""))


def _parse_compound(text: str, start: int) -> tuple[_SimpleSelector, int]:
    tag: str | None = None
    classes: set[str] = set()
    ids: set[str] = set()
    position = start
    length = len(text)
    while position < length:
        char = text[position]
        if char.isspace() or char in (",", ">"):
            break
        if char == ".":
            name, position = _read_identifier(text, position + 1)
            classes.add(name)
        elif char == "#":
            name, position = _read_identifier(text, position + 1)
            ids.add(name)
        else:
            if tag is not None or classes or ids:
                break
            name, position = _read_identifier(text, position)
            tag = name.lower()
    if tag is None and not classes and not ids:
        raise ValueError(f"Invalid selector syntax: {text!r}")
    return _SimpleSelector(tag=tag, classes=frozenset(classes), ids=frozenset(ids)), position


def _read_identifier(text: str, position: int) -> tuple[str, int]:
    if position >= len(text) or _IDENTIFIER_START_RE.match(text, position) is None:
        raise ValueError(f"Unsupported selector syntax: {text!r}")
    match = _IDENTIFIER_BODY_RE.match(text, position + 1)
    rest = match.group(0) if match is not None else ""
    return text[position] + rest, position + 1 + len(rest)


def _skip_whitespace(text: str, position: int) -> int:
    length = len(text)
    while position < length and text[position].isspace():
        position += 1
    return position


def _matches_chain(node: DOMNode, chain: _SelectorChain, root: DOMNode) -> bool:
    parts = chain.parts
    if not _matches_simple(node, parts[-1][0]):
        return False
    current = node
    for index in range(len(parts) - 2, -1, -1):
        previous = parts[index][0]
        combinator = parts[index][1]
        if combinator == _CHILD:
            parent = current.parentNode
            if parent is None or not _matches_simple(parent, previous):
                return False
            current = parent
        else:
            ancestor = current.parentNode
            found = False
            while True:
                if ancestor is None:
                    break
                if _matches_simple(ancestor, previous):
                    found = True
                    current = ancestor
                    break
                if ancestor is root:
                    break
                ancestor = ancestor.parentNode
            if not found:
                return False
    return True


def _matches_simple(node: DOMNode, simple: _SimpleSelector) -> bool:
    name = node.nodeName
    if not isinstance(name, str):
        return False
    if simple.tag is not None and name.lower() != simple.tag:
        return False
    if simple.ids:
        id_value = node.getAttribute("id")
        if id_value is None or id_value not in simple.ids:
            return False
    if simple.classes:
        class_value = node.getAttribute("class")
        if class_value is not None and not isinstance(class_value, str):
            return False
        if not class_value or not simple.classes <= set(class_value.split()):
            return False
    return True
