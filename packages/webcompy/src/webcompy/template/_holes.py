from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from webcompy.signal import SignalBase

HOLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)\s*\}\}")


@dataclass
class LiteralText:
    text: str


@dataclass
class Hole:
    var_path: str


def split_text(text: str) -> list[LiteralText | Hole]:
    parts: list[LiteralText | Hole] = []
    last_end = 0
    for match in HOLE_PATTERN.finditer(text):
        if match.start() > last_end:
            parts.append(LiteralText(text[last_end : match.start()]))
        parts.append(Hole(match.group(1)))
        last_end = match.end()
    if last_end < len(text):
        parts.append(LiteralText(text[last_end:]))
    return parts


def resolve_var(path: str, ctx: dict[str, Any]) -> Any:
    segments = path.split(".")
    current: Any = ctx
    for segment in segments:
        if isinstance(current, dict):
            if segment not in current:
                available = ", ".join(sorted(current.keys()))
                raise KeyError(f"Template variable '{segment}' not found in context (available: {available})")
            current = current[segment]
        else:
            if not hasattr(current, segment):
                raise KeyError(f"Template variable '{segment}' not found on {type(current).__name__}")
            current = getattr(current, segment)
    return current


def format_value(value: Any) -> str:
    """Shared formatter for `{{ }}` hole interpolation results.

    Used by three consumers that must agree on edge-case rendering:

    * ``resolve_holes`` for CSS text (Change 5 ``css_text_template``)
    * ``resolve_attr`` for static attribute values
    * ``resolve_attr`` for reactive attribute ``Computed`` closures

    Rules:

    * ``None`` → empty string (prevents ``str(None) == "None"`` leaking
      into CSS / attribute output)
    * ``SignalBase`` whose ``.value`` is ``None`` → empty string
    * ``SignalBase`` whose ``.value`` is a string → ``.value``
    * ``SignalBase`` whose ``.value`` is anything else → ``str(value)``
    * anything else → ``str(value)``
    """
    if value is None:
        return ""
    if isinstance(value, SignalBase):
        raw = value.value
        if raw is None:
            return ""
        return raw if isinstance(raw, str) else str(raw)
    return str(value)


def resolve_holes(text: str, ctx: dict[str, Any]) -> str:
    parts = split_text(text)
    if not parts:
        return ""
    rendered: list[str] = []
    for part in parts:
        if isinstance(part, LiteralText):
            rendered.append(part.text)
        else:
            rendered.append(format_value(resolve_var(part.var_path, ctx)))
    return "".join(rendered)
