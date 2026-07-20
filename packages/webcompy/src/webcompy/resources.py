from __future__ import annotations

from pathlib import Path

from webcompy.di import inject
from webcompy.exception import WebComPyException
from webcompy.ports._keys import RESOURCE_PORT_KEY


def _normalize_source(source: str | Path) -> str:
    if isinstance(source, str):
        path = source
    elif isinstance(source, Path):
        if source.is_absolute():
            raise WebComPyException(f"Absolute paths are not supported: {source}")
        path = source.as_posix()
    else:
        raise WebComPyException(f"Invalid source type: expected str or Path, got {type(source).__name__}")
    if ".." in path.split("/"):
        raise WebComPyException(f"Path contains '..' segments: {path}")
    return path


def _get_port():
    port = inject(RESOURCE_PORT_KEY, default=None)
    if port is None:
        raise WebComPyException(
            "RESOURCE_PORT_KEY not found in the current DI scope. "
            "load_text / load_bytes must be called from inside a render context."
        )
    return port


async def load_text(source: str | Path) -> str:
    path = _normalize_source(source)
    port = _get_port()
    return await port.load_text(path)


async def load_bytes(source: str | Path) -> bytes:
    path = _normalize_source(source)
    port = _get_port()
    return await port.load_bytes(path)
