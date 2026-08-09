from __future__ import annotations

from webcompy.di import inject
from webcompy.di._keys import HYDRATION_DATA_KEY
from webcompy.hydration._codec import decode, encode, register_type_handler
from webcompy.hydration._transfer_meta import (
    META_BODY_KEY,
    META_HEADER_NAME,
    apply_transfer_meta,
    encode_with_meta,
    merge_meta_into_body,
)


def has_resolved_data(component_id: str) -> bool:
    payload = inject(HYDRATION_DATA_KEY, default=None)
    if payload is None:
        return False
    return component_id in payload


__all__ = [
    "META_BODY_KEY",
    "META_HEADER_NAME",
    "apply_transfer_meta",
    "decode",
    "encode",
    "encode_with_meta",
    "has_resolved_data",
    "merge_meta_into_body",
    "register_type_handler",
]
