from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from webcompy.app._app import WebComPyApp

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


@contextmanager
def mock_app_run() -> Iterator[None]:
    original: Callable[..., Any] = WebComPyApp.run

    def _noop(self: object) -> None:
        pass

    WebComPyApp.run = _noop  # type: ignore[method-assign]
    try:
        yield
    finally:
        WebComPyApp.run = original  # type: ignore[method-assign]
