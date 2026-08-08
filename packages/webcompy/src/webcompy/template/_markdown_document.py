from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HeadingInfo:
    """A heading entry extracted from a rendered Markdown document.

    ``level`` is the heading depth (1-6), ``text`` is the resolved heading
    text with interpolated values, and ``id`` is the slug id injected into
    the corresponding heading element.
    """

    level: int
    text: str
    id: str
