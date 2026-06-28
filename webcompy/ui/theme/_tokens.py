"""Theme design tokens (color, shadow) for WebComPy's UI toolkit.

These values mirror the static tokens in ``webcompy/ui/_styles/tokens.css`` and
``webcompy/ui/_styles/tokens-dark.css`` and are used by ``ThemeManager`` to
inject per-theme CSS custom properties via the reactive style primitive
(``app.append_style(reactive_block(...))``) at runtime.

The reactive style is wrapped in ``@layer webcompy-dynamic`` (added by
``feat-reactive-app-style``), so it wins over the static ``@layer tokens``
defaults from ``tokens.css``. This lets a single source of truth
(``tokens.css``) define the light defaults while theme signals override
them reactively.

If a new token is added, add it to BOTH ``tokens.css`` AND ``LIGHT_TOKENS``
(``DARK_TOKENS`` is generated from overrides).
"""

from __future__ import annotations

from typing import Final

LIGHT_TOKENS: Final[dict[str, str]] = {
    "--color-bg": "#ffffff",
    "--color-bg-elevated": "#f6f8fa",
    "--color-bg-code": "#f6f8fa",
    "--color-bg-card": "#ffffff",
    "--color-fg": "#1f2328",
    "--color-fg-muted": "#57606a",
    "--color-fg-subtle": "#6e7781",
    "--color-link": "#0969da",
    "--color-link-hover": "#0550ae",
    "--color-accent": "#0969da",
    "--color-border": "#d0d7de",
    "--color-border-muted": "#d8dee4",
    "--color-success": "#1a7f37",
    "--color-danger": "#d1242f",
    "--color-warning": "#9a6700",
    "--shadow-sm": "0 1px 0 rgba(31, 35, 40, 0.04)",
    "--shadow-md": "0 3px 6px rgba(140, 149, 159, 0.15)",
    "--tok-kw": "#cf222e",
    "--tok-str": "#0a3069",
    "--tok-num": "#0550ae",
    "--tok-comment": "#6e7781",
    "--tok-fn": "#8250df",
    "--tok-builtin": "#953800",
    "--tok-decorator": "#953800",
    "--tok-op": "#1f2328",
    "--tok-punct": "#1f2328",
    "--tok-ident": "#1f2328",
}

DARK_TOKENS: Final[dict[str, str]] = {
    "--color-bg": "#0d1117",
    "--color-bg-elevated": "#161b22",
    "--color-bg-code": "#161b22",
    "--color-bg-card": "#161b22",
    "--color-fg": "#e6edf3",
    "--color-fg-muted": "#8d96a0",
    "--color-fg-subtle": "#6e7681",
    "--color-link": "#4493f8",
    "--color-link-hover": "#58a6ff",
    "--color-accent": "#4493f8",
    "--color-border": "#30363d",
    "--color-border-muted": "#21262d",
    "--color-success": "#3fb950",
    "--color-danger": "#f85149",
    "--color-warning": "#d29922",
    "--shadow-sm": "0 1px 0 rgba(0, 0, 0, 0.4)",
    "--shadow-md": "0 3px 6px rgba(0, 0, 0, 0.45)",
    "--tok-kw": "#ff7b72",
    "--tok-str": "#a5d6ff",
    "--tok-num": "#79c0ff",
    "--tok-comment": "#8b949e",
    "--tok-fn": "#d2a8ff",
    "--tok-builtin": "#ffa657",
    "--tok-decorator": "#ffa657",
    "--tok-op": "#e6edf3",
    "--tok-punct": "#e6edf3",
    "--tok-ident": "#e6edf3",
}


def render_tokens_css(tokens: dict[str, str], *, important: bool = False) -> str:
    """Render a token dict as a CSS declarations block (no surrounding braces)."""
    suffix = " !important" if important else ""
    return "\n  ".join(f"{name}: {value}{suffix};" for name, value in tokens.items())


__all__ = ["DARK_TOKENS", "LIGHT_TOKENS", "render_tokens_css"]
