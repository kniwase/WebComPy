from __future__ import annotations

from pathlib import Path

from webcompy.ports._resource import ResourceNotFoundError, ResourcePort


class ServerResourcePort(ResourcePort):
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
        resolved = self._resolve(path)
        try:
            text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ResourceNotFoundError(path, "server", reason=str(exc)) from exc
        self._recorded[path] = text.encode("utf-8")
        return text

    async def load_bytes(self, path: str) -> bytes:
        resolved = self._resolve(path)
        try:
            content = resolved.read_bytes()
        except OSError as exc:
            raise ResourceNotFoundError(path, "server", reason=str(exc)) from exc
        self._recorded[path] = content
        return content

    def get_recorded_resources(self) -> dict[str, bytes]:
        return dict(self._recorded)
