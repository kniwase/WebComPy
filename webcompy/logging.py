from typing import Any, Protocol, Tuple
from webcompy._browser._modules import browser as _browser
from logging import getLogger as _getLogger


class _Handler(Protocol):
    def debug(self, msg: str):
        ...

    def info(self, msg: str):
        ...

    def warn(self, msg: str):
        ...

    def error(self, msg: str):
        ...


_handler: _Handler = _browser.console if _browser else _getLogger("uvicorn")


def _convert_msg(values: Tuple[Any]):
    return "\t".join(map(str, values))


def debug(*values: Any):
    _handler.debug(_convert_msg(values))


def info(*values: Any):
    _handler.info(_convert_msg(values))


def warn(*values: Any):
    _handler.warn(_convert_msg(values))


def error(*values: Any):
    _handler.error(_convert_msg(values))
