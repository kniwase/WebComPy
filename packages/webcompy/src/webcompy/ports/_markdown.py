"""Markdown rendering port."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MarkdownPort(ABC):
    """Markdown rendering surface.

    Implementations convert Markdown source text into HTML exactly once per
    call; cacheable results are layered by the callers.
    """

    @abstractmethod
    def render(self, source: str) -> str:
        """Render Markdown source text to HTML.

        Args:
            source: Markdown source text.

        Returns:
            The rendered HTML.

        """
        ...
