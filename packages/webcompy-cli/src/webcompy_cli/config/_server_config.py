from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.types import ASGIApp


@dataclass
class WebComPyServerConfig:
    port: int = 8080
    dev: bool = False
    mounts: Callable[[], dict[str, ASGIApp]] | None = None


@dataclass
class LockfileSyncConfig:
    requirements_path: str | None = None
    sync_group: str | None = None
