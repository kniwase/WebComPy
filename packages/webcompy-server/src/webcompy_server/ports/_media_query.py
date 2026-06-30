from __future__ import annotations

from webcompy.ports._media_query import MediaQueryPort


class ServerMediaQueryPort(MediaQueryPort):
    def prefers_dark(self) -> bool:
        return False
