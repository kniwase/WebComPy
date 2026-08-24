"""Browser storage composables for ``localStorage`` and ``sessionStorage``."""

from webcompy.storage._composable import use_local_storage, use_session_storage

__all__ = [
    "use_local_storage",
    "use_session_storage",
]
