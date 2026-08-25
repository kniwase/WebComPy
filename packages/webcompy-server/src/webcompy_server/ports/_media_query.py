"""Server-side media query port."""

from __future__ import annotations

from webcompy.ports._media_query import MediaQueryPort


class ServerMediaQueryPort(MediaQueryPort):
    """Server-side media query port returning defaults."""

    def prefers_dark(self) -> bool:
        """Return whether the user prefers a dark theme.

        Returns:
            ``False`` on the server.

        """
        return False

    def prefers_reduced_motion(self) -> bool:
        """Return whether the user prefers reduced motion.

        Returns:
            ``False`` on the server.

        """
        return False
