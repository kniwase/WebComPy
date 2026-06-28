from __future__ import annotations

from abc import ABC, abstractmethod


class MediaQueryPort(ABC):
    @abstractmethod
    def prefers_dark(self) -> bool:
        """Return whether the user prefers a dark color scheme.

        In the browser this reads the ``(prefers-color-scheme: dark)`` media
        query. On the server it returns ``False`` by default (the framework
        cannot know the user's preference at SSG / SSR time without a cookie).
        """
        ...
