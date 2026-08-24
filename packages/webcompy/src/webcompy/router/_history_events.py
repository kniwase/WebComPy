"""Compatibility alias of the history port under the historical ``Location`` name."""

from __future__ import annotations

from webcompy.ports._history import HistoryPort

type Location = HistoryPort

__all__ = ["Location"]
