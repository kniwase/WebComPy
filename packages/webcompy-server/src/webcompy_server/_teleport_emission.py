"""Server-side emission of teleported children into the rendered document."""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING, cast

from webcompy.di import inject
from webcompy.di._keys import _TELEPORT_REGISTRY_KEY
from webcompy.elements.types._teleport import (
    _PendingTeleportEntry,
    _TeleportTargetRegistry,
    block_end_data,
    block_start_data,
)
from webcompy.ports._dom import DOMNode
from webcompy.ports._keys import DOM_PORT_KEY

if TYPE_CHECKING:
    from webcompy_server.ports._dom import ServerDOMPort

_logger = getLogger(__name__)


async def emit_teleport_blocks(app_root_node: DOMNode | None) -> None:
    """Render pending teleport children into their resolved targets.

    Drains the per-context registry repeatedly so teleports nested inside
    already-emitted content are emitted in later rounds, with their anchors
    mounted inside the freshly created subtree.

    Args:
        app_root_node: The application mount container node used for
            rejection checks; ``None`` when unavailable.

    Returns:
        ``None``.

    """
    registry = cast("_TeleportTargetRegistry | None", inject(_TELEPORT_REGISTRY_KEY, default=None))
    if registry is None:
        return
    dom_port = inject(DOM_PORT_KEY)
    while True:
        entries = registry.take_pending_entries()
        if not entries:
            break
        for entry in entries:
            await _emit_entry(dom_port, registry, entry, app_root_node)


async def _emit_entry(
    dom_port: ServerDOMPort,
    registry: _TeleportTargetRegistry,
    entry: _PendingTeleportEntry,
    app_root_node: DOMNode | None,
) -> None:
    teleport = entry.teleport
    try:
        target = dom_port.query_selector(entry.to)
    except ValueError:
        _logger.warning("Teleport target '%s' uses unsupported selector syntax; emitting anchor only.", entry.to)
        return
    if target is None:
        _logger.warning("Teleport target '%s' not found in the server document; emitting anchor only.", entry.to)
        return
    if _is_rejected_target(target, app_root_node):
        _logger.warning(
            "Teleport target '%s' resolves inside the application subtree or head; emitting anchor only.",
            entry.to,
        )
        return
    teleport._target_node = target
    registry.register(target, teleport)
    start = dom_port.create_comment(block_start_data(entry.ordinal, entry.to))
    end = dom_port.create_comment(block_end_data(entry.ordinal))
    target.appendChild(start)
    index = target.childNodes.length
    for child in entry.children:
        child._node_idx = index
        await child._render()
        index += child._node_count
    target.appendChild(end)


def _is_rejected_target(node: DOMNode, app_root_node: DOMNode | None) -> bool:
    current: DOMNode | None = node
    while current is not None:
        if current.nodeName.lower() == "head":
            return True
        if app_root_node is not None and current is app_root_node:
            return True
        current = current.parentNode
    return False
