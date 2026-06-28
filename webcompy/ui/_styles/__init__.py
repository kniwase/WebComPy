from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.abc import Traversable


_STYLES_PACKAGE = "webcompy.ui._styles"
_STYLES_FILES: tuple[str, ...] = (
    "index.css",
    "tokens.css",
    "reset.css",
    "components.css",
    "code-block.css",
    "syntax-theme.css",
)


def get_styles_dir() -> Traversable:
    return files("webcompy").joinpath("ui", "_styles")  # type: ignore[return-value]


def get_styles_files() -> dict[str, bytes]:
    """Return a mapping of relative filename to file content for the framework CSS.

    Works both for installed wheels and for source-tree development because
    ``importlib.resources.files`` resolves to the package data on disk in
    either case.
    """
    styles_dir = get_styles_dir()
    result: dict[str, bytes] = {}
    for name in _STYLES_FILES:
        entry = styles_dir.joinpath(name)
        if not entry.is_file():
            continue
        with entry.open("rb") as fh:
            result[name] = fh.read()
    return result


def get_styles_file(name: str) -> bytes | None:
    if name not in _STYLES_FILES:
        return None
    entry = get_styles_dir().joinpath(name)
    if not entry.is_file():
        return None
    with entry.open("rb") as fh:
        return fh.read()


__all__ = [
    "get_styles_dir",
    "get_styles_file",
    "get_styles_files",
]
