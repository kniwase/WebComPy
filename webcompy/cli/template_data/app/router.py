from webcompy.router import Router
from .components.home import Home
from .components.fizzbuzz import Fizzbuzz
from .components.input import InOutSample
from .components.not_found import NotFound

router = Router(
    {"path": "/", "component": Home},
    {"path": "/fizzbuzz", "component": Fizzbuzz},
    {"path": "/input", "component": InOutSample},
    default=NotFound,
    mode="history",
    base_url="/WebComPy"
)
