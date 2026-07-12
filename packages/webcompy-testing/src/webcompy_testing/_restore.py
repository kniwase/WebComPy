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
    """Restore signal values for testing round-trip scenarios.

    Directly assigns each value to ``signal._value`` without re-decoding
    or triggering reactive notifications. Intended for use in test code
    that manually constructs signal members and hydration data; not part
    of the production hydration pipeline (which uses factory-skip via
    ``use_state()`` / ``use_reactive_list()`` / ``use_reactive_dict()``).

    Callers that construct signals_data by hand should run ``decode()``
    on each value before passing it in.
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
