from __future__ import annotations

from logging import getLogger
from typing import Any

_logger = getLogger(__name__)


def _get_component_id(component: Any) -> str:
    prop = getattr(component, "_property", None)
    if isinstance(prop, dict):
        return str(prop.get("component_id", ""))
    return ""


def restore_signal_values(
    component: Any,
    signals_data: dict[str, Any] | None,
) -> None:
    """Restore signal values from a (already-decoded) transfer payload.

    The dictionary passed in is expected to have been produced by
    ``deserialize_payload()``, which has already run every value through
    the codec's ``decode()``. This function therefore assigns each value
    directly to ``signal._value`` without re-decoding, bypassing
    ``set_value()`` to avoid triggering reactive notifications.

    Callers that construct signals_data by hand (e.g. tests) should run
    ``decode()`` on each value before passing it in.
    """
    if not signals_data:
        return
    members = getattr(component, "__signal_members__", None)
    if not members:
        return
    component_id = _get_component_id(component)
    for attr_name, value in signals_data.items():
        signal = members.get(attr_name)
        if signal is None:
            _logger.debug(
                "Skipping signal restore for %s.%s: not in __signal_members__",
                component_id,
                attr_name,
            )
            continue
        try:
            signal._value = value
        except Exception:
            _logger.exception(
                "Failed to restore signal value for %s.%s",
                component_id,
                attr_name,
            )
