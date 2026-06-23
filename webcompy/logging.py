from logging import getLogger as _getLogger
from typing import Any, Protocol

from webcompy.utils._environment import ENVIRONMENT


class _Handler(Protocol):
    def debug(self, msg: str): ...

    def info(self, msg: str): ...

    def warn(self, msg: str): ...

    def error(self, msg: str): ...


if ENVIRONMENT == "pyscript":
    from pyscript import context

    _handler: _Handler = context.window.console
else:
    _handler = _getLogger("uvicorn")


def _convert_msg(values: tuple[Any]):
    return "\t".join(map(str, values))


def debug(*values: Any):
    _handler.debug(_convert_msg(values))


def info(*values: Any):
    _handler.info(_convert_msg(values))


def warn(*values: Any):
    _handler.warn(_convert_msg(values))


def warning(*values: Any):
    _handler.warn(_convert_msg(values))


def error(*values: Any):
    _handler.error(_convert_msg(values))
