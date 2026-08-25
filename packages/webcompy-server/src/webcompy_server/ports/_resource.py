"""Server-side resource port for app-package files."""

from __future__ import annotations

from pathlib import Path

from webcompy.ports._resource import ResourceNotFoundError, ResourcePort


class ServerResourcePort(ResourcePort):
    """Server-side resource loader that reads files from the app package.

    Args:
        app_package_path: Filesystem path of the app package root.
        allow_list: Set of allowed relative resource paths.

    """

    def __init__(
        self,
        app_package_path: Path,
        allow_list: frozenset[str],
    ) -> None:
        self._app_package_path = app_package_path
        self._allow_list = allow_list
        self._recorded: dict[str, bytes] = {}

    def _validate(self, path: str) -> None:
        if not path:
            raise ResourceNotFoundError(path or "<empty>", "server", reason="empty path")
        if path.startswith("/"):
            raise ResourceNotFoundError(path, "server", reason="path must be relative")
        segments = path.split("/")
        if ".." in segments:
            raise ResourceNotFoundError(path, "server", reason="path contains '..' segments")
        if path not in self._allow_list:
            raise ResourceNotFoundError(path, "server", reason="not in allow-list")

    def _resolve(self, path: str) -> Path:
        self._validate(path)
        resolved = (self._app_package_path / path).resolve()
        root_resolved = self._app_package_path.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise ResourceNotFoundError(path, "server", reason="path escapes app package") from exc
        return resolved

    async def load_text(self, path: str) -> str:
        """Load a text resource.

        Args:
            path: Relative resource path.

        Returns:
            Text content of the resource.

        Raises:
            ResourceNotFoundError: If the resource is missing or invalid.

        """
        resolved = self._resolve(path)
        try:
            text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ResourceNotFoundError(path, "server", reason=str(exc)) from exc
        self._recorded[path] = text.encode("utf-8")
        return text

    async def load_bytes(self, path: str) -> bytes:
        """Load a binary resource.

        Args:
            path: Relative resource path.

        Returns:
            Binary content of the resource.

        Raises:
            ResourceNotFoundError: If the resource is missing or invalid.

        """
        resolved = self._resolve(path)
        try:
            content = resolved.read_bytes()
        except OSError as exc:
            raise ResourceNotFoundError(path, "server", reason=str(exc)) from exc
        self._recorded[path] = content
        return content

    def get_recorded_resources(self) -> dict[str, bytes]:
        """Return recorded resource contents.

        Returns:
            Mapping of paths to recorded byte contents.

        """
        return dict(self._recorded)

    def fresh(self) -> ServerResourcePort:
        """Create a fresh port sharing the same configuration.

        Returns:
            New ``ServerResourcePort`` with the same paths.

        """
        return ServerResourcePort(
            app_package_path=self._app_package_path,
            allow_list=self._allow_list,
        )
