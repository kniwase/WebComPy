"""Media query port for user-preference reads."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MediaQueryPort(ABC):
    """User-preference media queries (dark color scheme and reduced motion)."""

    @abstractmethod
    def prefers_dark(self) -> bool:
        """Return whether the user prefers a dark color scheme.

        In the browser this reads the ``(prefers-color-scheme: dark)`` media
        query. On the server it returns ``False`` by default (the framework
        cannot know the user's preference at SSG / SSR time without a cookie).
        """
        ...

    @abstractmethod
    def prefers_reduced_motion(self) -> bool:
        """Return whether the user prefers reduced motion.

        In the browser this reads the ``(prefers-reduced-motion: reduce)``
        media query. On the server it returns ``False`` by default (the
        framework cannot know the user's preference at SSG / SSR time without
        a cookie).
        """
        ...
