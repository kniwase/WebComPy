from __future__ import annotations

from webcompy.di import inject
from webcompy.router._keys import RouterKey
from webcompy.router._router import Router


def useRouter() -> Router:
    return inject(RouterKey)
