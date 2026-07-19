from __future__ import annotations

from abc import ABC, abstractmethod


class ResourceNotFoundError(Exception):
    """Raised when a resource cannot be loaded by a ``ResourcePort`` implementation.

    The message includes the requested package-relative path and the
    implementation context (e.g., ``"server"`` or ``"browser"``).
    """

    def __init__(self, path: str, context: str, reason: str = "") -> None:
        location = f" ({context})" if context else ""
        detail = f": {reason}" if reason else ""
        super().__init__(f"Resource not found: {path}{location}{detail}")
        self.path = path
        self.context = context


class ResourcePort(ABC):
    """Abstract async port for accessing application package resources.

    Resources are identified by package-relative POSIX-style paths (forward
    slashes, no leading slash, no ``..`` segments). Implementations resolve the
    path to content (text or bytes) appropriate for the runtime environment
    and raise :class:`ResourceNotFoundError` when the resource cannot be
    obtained.
    """

    @abstractmethod
    async def load_text(self, path: str) -> str:
        """Load a resource as UTF-8 text."""
        ...

    @abstractmethod
    async def load_bytes(self, path: str) -> bytes:
        """Load a resource as raw bytes."""
        ...
