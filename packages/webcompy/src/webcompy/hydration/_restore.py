from __future__ import annotations

from logging import getLogger
from typing import Any

from webcompy.hydration._codec import decode

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
    if not signals_data:
        return
    members = getattr(component, "__signal_members__", None)
    if not members:
        return
    component_id = _get_component_id(component)
    for attr_name, encoded_value in signals_data.items():
        signal = members.get(attr_name)
        if signal is None:
            _logger.debug(
                "Skipping signal restore for %s.%s: not in __signal_members__",
                component_id,
                attr_name,
            )
            continue
        try:
            signal._value = decode(encoded_value)
        except Exception:
            _logger.exception(
                "Failed to restore signal value for %s.%s",
                component_id,
                attr_name,
            )
