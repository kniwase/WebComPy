from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WebComPyServerConfig:
    port: int = 8080
    dev: bool = False


@dataclass
class LockfileSyncConfig:
    requirements_path: str | None = None
    sync_group: str | None = None
