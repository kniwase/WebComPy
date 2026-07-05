from __future__ import annotations

from typing import Any

from webcompy.di import inject
from webcompy.di._keys import HYDRATION_DATA_KEY, HYDRATION_SIGNAL_DATA_KEY
from webcompy.hydration._codec import decode, encode, register_type_handler
from webcompy.hydration._restore import restore_signal_values


def has_resolved_data(component_id: str) -> bool:
    payload = inject(HYDRATION_DATA_KEY, default=None)
    if payload is None:
        return False
    return component_id in payload


def get_signal_transfer_data(component_id: str) -> dict[str, Any] | None:
    payload = inject(HYDRATION_SIGNAL_DATA_KEY, default=None)
    if payload is None:
        return None
    return payload.get(component_id)


__all__ = [
    "decode",
    "encode",
    "has_resolved_data",
    "register_type_handler",
    "restore_signal_values",
]
