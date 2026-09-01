"""Shared overlay utilities for focus management and document listeners."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from typing import Any

from webcompy.components._hooks import _register_before_destroy_chained
from webcompy.di import inject
from webcompy.ports._dom import DOMNode, DOMPort
from webcompy.ports._host import HostPort
from webcompy.ports._keys import DOM_PORT_KEY, HOST_PORT_KEY
from webcompy.ui.headless._dom_id import component_dom_id


def overlay_dom_id(kind: str, context: Any) -> str:
    """Return a per-instance DOM id for an overlay element.

    Delegates to :func:`component_dom_id`, the shared hydration-stable
    id helper for all UI primitives.

    Args:
        kind: Element kind used as the id prefix (e.g. ``modal-panel``).
        context: Component context of the overlay instance.

    Returns:
        The generated DOM id string.

    """
    return component_dom_id(kind, context)


def _get_document_active_element() -> DOMNode | None:
    """Return ``document.activeElement`` via the Host port or ``None`` on the server."""
    try:
        port: HostPort | None = inject(HOST_PORT_KEY, default=None)
    except Exception:
        return None
    if port is None:
        return None
    try:

        def _wrapper(doc: Any | None) -> Any:
            if doc is not None:
                return getattr(doc, "activeElement", None)
            return None

        getter = port.create_js_global_getter(
            "document",
            wrapper=_wrapper,
        )
        active = getter()
        return active  # type: ignore[return-value]
    except Exception:
        return None


def capture_active_element() -> DOMNode | None:
    """Capture the currently focused element for later restoration.

    Returns:
        The active element, or ``None`` when not in a browser environment.

    """
    return _get_document_active_element()


def restore_focus(captured: DOMNode | None) -> None:
    """Restore focus to ``captured`` when it remains in the document.

    Args:
        captured: Element captured by :func:`capture_active_element`.

    """
    if captured is None:
        return
    try:
        is_connected = getattr(captured, "isConnected", True)
        if not is_connected:
            return
    except Exception:
        is_connected = True
    try:
        focus_fn = getattr(captured, "focus", None)
        if focus_fn is not None:
            focus_fn()
    except Exception:
        logging.warning("overlay focus restore failed", exc_info=True)


def _node_is_focusable(node: DOMNode) -> bool:
    """Return whether ``node`` is focusable per the overlay trap definition."""
    tag = node.nodeName.upper()
    if tag == "BUTTON" and node.getAttribute("disabled") is not None:
        return False
    if tag in ("INPUT", "SELECT", "TEXTAREA") and node.getAttribute("disabled") is not None:
        return False
    tab_index_raw = node.getAttribute("tabindex")
    if tab_index_raw is not None and tab_index_raw.strip() == "-1":
        return False
    if tag == "A" and node.getAttribute("href") is not None:
        return True
    if tag in ("BUTTON", "SELECT", "TEXTAREA", "INPUT"):
        return True
    if tag in ("AUDIO", "VIDEO") and node.getAttribute("controls") is not None:
        return True
    if node.getAttribute("contenteditable") == "true":
        return True
    if tab_index_raw is not None:
        stripped = tab_index_raw.strip()
        try:
            if int(stripped) >= 0:
                return True
        except ValueError:
            return True
    return False


def get_focusable_elements(root: DOMNode | None) -> list[DOMNode]:
    """Return focusable descendants of ``root`` in document order.

    Args:
        root: Overlay root node to search within.

    Returns:
        Focusable element nodes found inside ``root``.

    """
    if root is None:
        return []
    try:
        dom: DOMPort | None = inject(DOM_PORT_KEY, default=None)
    except Exception:
        dom = None
    if dom is None:
        return _collect_focusable_direct(root)
    try:
        candidates = dom.query_selector_all("*", root=root)
    except Exception:
        candidates = _collect_focusable_direct(root)
        return [n for n in candidates if _node_is_focusable(n)]
    focusable = [n for n in candidates if _node_is_focusable(n)]
    return focusable


def _collect_focusable_direct(root: DOMNode) -> list[DOMNode]:
    collected: list[DOMNode] = []
    stack: list[DOMNode] = [root]
    while stack:
        node = stack.pop()
        if node.nodeType == 1 and _node_is_focusable(node) and node is not root:
            collected.append(node)
        children = node.childNodes
        for idx in range(children.length - 1, -1, -1):
            stack.append(children[idx])
    collected.reverse()
    return collected


def focus_initial(root: DOMNode) -> None:
    """Move focus into ``root``: first focusable element, or the panel itself.

    Args:
        root: Overlay panel node.

    """
    focusable = get_focusable_elements(root)
    if focusable:
        try:
            focusable[0].focus()
        except Exception:
            logging.warning("overlay focus initial failed", exc_info=True)
        return
    try:
        if root.getAttribute("tabindex") is None:
            root.setAttribute("tabindex", "-1")
        root.focus()
    except Exception:
        logging.warning("overlay focus initial fallback failed", exc_info=True)


def trap_focus(root: DOMNode) -> Callable[[], None]:
    """Install a keydown handler on ``root`` that cycles Tab at boundaries.

    Args:
        root: Overlay panel node receiving the listener.

    Returns:
        Cleanup function removing the handler.

    """

    def _on_keydown(event: Any) -> None:
        key = getattr(event, "key", None)
        if key is None and isinstance(event, dict):
            key = event.get("key")
        if key != "Tab":
            return
        focusable = get_focusable_elements(root)
        if not focusable:
            return
        active = _get_document_active_element()
        shift = bool(getattr(event, "shiftKey", False) or (isinstance(event, dict) and event.get("shiftKey")))
        first = focusable[0]
        last = focusable[-1]
        if active is None:
            with contextlib.suppress(Exception):
                first.focus()
            _prevent(event)
            return
        if not shift and active is last:
            with contextlib.suppress(Exception):
                first.focus()
            _prevent(event)
        elif shift and active is first:
            with contextlib.suppress(Exception):
                last.focus()
            _prevent(event)

    try:
        root.addEventListener("keydown", _on_keydown)
    except Exception:
        logging.warning("overlay trap_focus addEventListener failed", exc_info=True)
        return lambda: None

    def _remove() -> None:
        with contextlib.suppress(Exception):
            root.removeEventListener("keydown", _on_keydown)

    _register_before_destroy_chained(_remove)
    return _remove


def _prevent(event: Any) -> None:
    try:
        fn = getattr(event, "preventDefault", None)
        if fn is not None:
            fn()
    except Exception:
        pass


def use_document_escape(
    handler: Callable[[], None],
    *,
    enabled: bool = True,
) -> Callable[[], None]:
    """Register a document keydown listener for Escape when enabled.

    Args:
        handler: Called when Escape is pressed.
        enabled: Whether the listener is active.

    Returns:
        Cleanup function.

    """
    if not enabled:
        return lambda: None

    def _on_keydown(event: Any) -> None:
        key = getattr(event, "key", None)
        if key is None and isinstance(event, dict):
            key = event.get("key")
        if key == "Escape":
            handler()

    try:
        dom: DOMPort | None = inject(DOM_PORT_KEY, default=None)
    except Exception:
        dom = None
    if dom is None:
        return lambda: None
    remove = dom.add_document_event_listener("keydown", _on_keydown)
    _register_before_destroy_chained(remove)
    return remove


def use_document_outside_click(
    panel: DOMNode,
    trigger: DOMNode | None,
    handler: Callable[[], None],
    *,
    enabled: bool = True,
) -> Callable[[], None]:
    """Register a document click listener closing on outside click.

    Args:
        panel: Overlay root node treated as inside.
        trigger: Optional trigger element excluded from outside.
        handler: Called when an outside click is detected.
        enabled: Whether the listener is active.

    Returns:
        Cleanup function.

    """
    if not enabled:
        return lambda: None

    def _node_contains(ancestor: Any, target: Any | None) -> bool:
        if target is None or ancestor is None:
            return False
        node: Any = target
        visited: set[int] = set()
        while node is not None:
            if id(node) in visited:
                break
            visited.add(id(node))
            if node is ancestor:
                return True
            try:
                node = node.parentNode
            except Exception:
                return False
        return False

    def _on_click(event: Any) -> None:
        target = getattr(event, "target", None)
        if target is None and isinstance(event, dict):
            target = event.get("target")
        if _node_contains(panel, target):
            return
        if trigger is not None and _node_contains(trigger, target):
            return
        handler()

    try:
        dom: DOMPort | None = inject(DOM_PORT_KEY, default=None)
    except Exception:
        dom = None
    if dom is None:
        return lambda: None
    remove = dom.add_document_event_listener("click", _on_click)
    _register_before_destroy_chained(remove)
    return remove
