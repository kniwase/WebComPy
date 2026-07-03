from __future__ import annotations

from webcompy.di import inject
from webcompy.di._keys import HYDRATION_DATA_KEY


def has_resolved_data(component_id: str) -> bool:
    payload = inject(HYDRATION_DATA_KEY, default=None)
    if payload is None:
        return False
    return component_id in payload


__all__ = [
    "has_resolved_data",
]
