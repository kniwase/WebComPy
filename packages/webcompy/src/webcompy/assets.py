from __future__ import annotations

import importlib.resources
from pathlib import PurePosixPath


def load_asset(key: str) -> bytes:
    try:
        from app._assets_registry import _REGISTRY
    except ModuleNotFoundError:
        raise AssetNotFoundError(key) from None

    if key not in _REGISTRY:
        raise AssetNotFoundError(key)

    resource_path = _REGISTRY[key]
    parts = PurePosixPath(resource_path).parts
    package = parts[0]
    subpath = PurePosixPath(*parts[1:])

    try:
        ref = importlib.resources.files(package).joinpath(str(subpath))
        return ref.read_bytes()
    except (FileNotFoundError, ModuleNotFoundError) as e:
        raise AssetNotFoundError(key) from e


class AssetNotFoundError(Exception):
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Asset not found: {key}")
