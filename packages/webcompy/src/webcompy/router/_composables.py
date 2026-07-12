from __future__ import annotations

from webcompy.di import inject
from webcompy.router._keys import RouterKey
from webcompy.router._router import Router


def use_router() -> Router:
    return inject(RouterKey)
