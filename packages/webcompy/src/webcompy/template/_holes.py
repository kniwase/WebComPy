from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.signal import Computed, SignalBase
from webcompy.template._expression import (
    ExpressionPlan,
    compile_expression,
    evaluate,
    resolve_scope,
)

PROTECTED_LBRACE_PLACEHOLDER = "\x00wc-lb\x00"


def protect_lbrace(text: str) -> str:
    return text.replace("{", PROTECTED_LBRACE_PLACEHOLDER)


def restore_protected(text: str) -> str:
    return text.replace(PROTECTED_LBRACE_PLACEHOLDER, "{")


@dataclass
class LiteralText:
    text: str


@dataclass
class Hole:
    expr_source: str
    plan: ExpressionPlan


def _scan_hole_end(text: str, start: int) -> int | None:
    depth = 0
    quote: str | None = None
    i = start
    while i < len(text):
        ch = text[i]
        if quote is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            if depth == 0:
                if i + 1 < len(text) and text[i + 1] == "}":
                    return i
                raise WebComPyException(f"Unbalanced '}}' in template expression: {text!r}")
            depth -= 1
        i += 1
    return None


def split_text(text: str, *, strict: bool = False) -> list[LiteralText | Hole]:
    parts: list[LiteralText | Hole] = []
    buf: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "{" and i + 1 < len(text) and text[i + 1] == "{":
            if buf:
                parts.append(LiteralText("".join(buf)))
                buf = []
            try:
                end = _scan_hole_end(text, i + 2)
            except WebComPyException:
                if strict:
                    raise
                buf.append(text[i])
                i += 1
                continue
            if end is not None:
                expr_source = text[i + 2 : end].strip()
                try:
                    plan = compile_expression(expr_source)
                except WebComPyException:
                    if strict:
                        raise
                    buf.append(text[i])
                    i += 1
                    continue
                parts.append(Hole(expr_source=expr_source, plan=plan))
                i = end + 2
                continue
            elif strict:
                raise WebComPyException(f"Unclosed {{{{ }}}} hole in template: ...{text[i : i + 20]!r}...")
            else:
                buf.append(text[i])
                i += 1
                continue
        buf.append(text[i])
        i += 1
    if buf:
        parts.append(LiteralText("".join(buf)))
    if strict:
        for part in parts:
            if isinstance(part, LiteralText):
                _check_stale_braces(part.text)
    return parts


def _check_stale_braces(text: str) -> None:
    for j in range(len(text) - 1):
        if text[j] == "{" and text[j + 1] == "{":
            raise WebComPyException(f"Unclosed or malformed expression near {text[j : j + 15]!r} in template")


def _lookup(current: Any, segment: str) -> Any:
    if isinstance(current, dict):
        if segment not in current:
            available = ", ".join(sorted(current.keys()))
            raise KeyError(f"Template variable '{segment}' not found in context (available: {available})")
        return current[segment]
    if not hasattr(current, segment):
        raise KeyError(f"Template variable '{segment}' not found on {type(current).__name__}")
    return getattr(current, segment)


def _resolve_segments(segments: list[str], ctx: dict[str, Any]) -> Any:
    current: Any = ctx
    for segment in segments:
        if isinstance(current, SignalBase):
            current = current.value
        current = _lookup(current, segment)
    return current


def resolve_var(path: str, ctx: dict[str, Any]) -> Any:
    segments = path.split(".")
    current: Any = ctx
    for segment in segments:
        if isinstance(current, SignalBase):
            return Computed(lambda segments=segments, ctx=ctx: _resolve_segments(segments, ctx))
        current = _lookup(current, segment)
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
            plan = part.plan
            if plan.is_plain_path:
                value = resolve_var(part.expr_source, ctx)
            else:
                scope = resolve_scope(plan, ctx)
                value = evaluate(plan, scope)
            rendered.append(format_value(value))
    return "".join(rendered)
