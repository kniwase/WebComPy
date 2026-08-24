"""Template router configuration."""

from webcompy.router import Router

from .components.fizzbuzz import FizzbuzzPage
from .components.home import HomePage
from .components.input import InOutSample
from .components.not_found import NotFound

router = Router(
    {"path": "/", "component": HomePage},
    {"path": "/fizzbuzz", "component": FizzbuzzPage},
    {"path": "/input", "component": InOutSample},
    default=NotFound,
    mode="history",
    base_url="",
)
