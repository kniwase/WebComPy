"""``use_router`` composable for resolving the active ``Router``."""

from __future__ import annotations

from webcompy.di import inject
from webcompy.router._keys import RouterKey
from webcompy.router._router import Router


def use_router() -> Router:
    """Resolve the application ``Router`` from the active DI scope.

    Returns:
        The ``Router`` provided in the current DI scope.

    """
    return inject(RouterKey)
