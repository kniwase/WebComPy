"""Hydration-stable per-instance DOM id generation for UI primitives."""

from __future__ import annotations

from typing import Any


def component_dom_id(kind: str, context: Any) -> str:
    """Return a per-instance DOM id for a component element.

    The id is derived from the component instance's hydration-stable
    transfer id, so ids are unique among the instances on a page and
    identical between the server-rendered output and the hydrated
    client tree. The ``#`` ordinal separator of the transfer id is
    replaced with ``-`` to keep the value usable in CSS selectors.

    Args:
        kind: Element kind used as the id prefix (e.g. ``tabs-panel``).
        context: Component context of the component instance.

    Returns:
        The generated DOM id string.

    """
    raw = getattr(context, "transfer_id", "") or ""
    safe = raw.replace("#", "-")
    return f"webcompy-{kind}-{safe}"
