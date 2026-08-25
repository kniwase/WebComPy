"""Server configuration dataclasses."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.types import ASGIApp


@dataclass
class WebComPyServerConfig:
    """Configuration for the development server and ASGI mounts.

    Args:
        port: TCP port the server listens on.
        dev: Whether to run in development mode with live reload.
        mounts: Callable returning additional ``{prefix: app}`` ASGI mounts.

    Attributes:
        port: TCP port the server listens on.
        dev: Whether to run in development mode with live reload.
        mounts: Callable returning additional ``{prefix: app}`` ASGI mounts.

    """

    port: int = 8080
    dev: bool = False
    mounts: Callable[[], dict[str, ASGIApp]] | None = None


@dataclass
class LockfileSyncConfig:
    """Configuration for syncing the lock file with project manifests.

    Args:
        requirements_path: Path to the ``requirements.txt`` file used for
            ``sync`` and ``export``, or ``None`` to auto-discover.
        sync_group: Optional dependency group name in ``pyproject.toml``
            to compare against the lock file.

    Attributes:
        requirements_path: Path to the ``requirements.txt`` file used for
            ``sync`` and ``export``, or ``None`` to auto-discover.
        sync_group: Optional dependency group name in ``pyproject.toml``
            to compare against the lock file.

    """

    requirements_path: str | None = None
    sync_group: str | None = None
