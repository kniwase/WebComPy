from __future__ import annotations

from webcompy.di._key import InjectKey
from webcompy.di._provide_inject import inject
from webcompy.router._router import Router

RouterKey: InjectKey[Router] = InjectKey("webcompy-router")


def useRouter() -> Router:
    return inject(RouterKey)
