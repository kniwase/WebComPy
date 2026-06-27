from __future__ import annotations

import re
from pathlib import Path

STYLES_DIR = Path(__file__).resolve().parent.parent / "webcompy" / "ui" / "_styles"


COLOR_TOKENS = [
    "color-bg",
    "color-bg-elevated",
    "color-bg-code",
    "color-bg-card",
    "color-fg",
    "color-fg-muted",
    "color-fg-subtle",
    "color-link",
    "color-link-hover",
    "color-accent",
    "color-border",
    "color-border-muted",
    "color-success",
    "color-danger",
    "color-warning",
]

SYNTAX_TOKENS = [
    "tok-kw",
    "tok-str",
    "tok-num",
    "tok-comment",
    "tok-fn",
    "tok-builtin",
    "tok-decorator",
    "tok-op",
    "tok-punct",
    "tok-ident",
]


def _css_text(name: str) -> str:
    return (STYLES_DIR / name).read_text(encoding="utf-8")


def test_required_files_exist() -> None:
    expected = [
        "tokens.css",
        "tokens-dark.css",
        "reset.css",
        "components.css",
        "code-block.css",
        "syntax-theme.css",
        "index.css",
    ]
    for name in expected:
        assert (STYLES_DIR / name).is_file(), f"Missing CSS file: {name}"


def test_index_css_declares_layer_order() -> None:
    css = _css_text("index.css")
    assert re.search(
        r"@layer\s+reset,\s*tokens,\s*components,\s*webcompy-scope,\s*webcompy-dynamic\s*;",
        css,
    ), "index.css must declare '@layer reset, tokens, components, webcompy-scope, webcompy-dynamic;' once"


def test_tokens_light_defined_for_every_color_token() -> None:
    css = _css_text("tokens.css")
    for token in COLOR_TOKENS + SYNTAX_TOKENS:
        assert f"--{token}" in css, f"Light theme missing token --{token}"


def test_tokens_dark_defined_for_every_color_token() -> None:
    css = _css_text("tokens-dark.css")
    for token in COLOR_TOKENS + SYNTAX_TOKENS:
        assert f"--{token}" in css, f"Dark theme missing token --{token}"


def test_tokens_dark_selector_targets_data_theme_dark() -> None:
    css = _css_text("tokens-dark.css")
    assert ':root[data-theme="dark"]' in css, 'tokens-dark.css must define :root[data-theme="dark"] selector'


def test_tokens_dark_includes_system_preference_fallback() -> None:
    css = _css_text("tokens-dark.css")
    assert "prefers-color-scheme: dark" in css, (
        "tokens-dark.css must include @media (prefers-color-scheme: dark) for system mode"
    )


def test_tokens_declares_color_scheme_on_root() -> None:
    css = _css_text("tokens.css")
    assert re.search(r":root\s*\{[^}]*color-scheme:\s*light\s+dark", css, re.DOTALL), (
        "tokens.css must declare 'color-scheme: light dark' on :root"
    )


def test_reset_layer_used() -> None:
    css = _css_text("reset.css")
    assert "@layer reset" in css, "reset.css must be in the reset layer"


def test_components_layer_used() -> None:
    css = _css_text("components.css")
    assert "@layer components" in css, "components.css must be in the components layer"


def test_code_block_uses_scope_for_italic_comment() -> None:
    css = _css_text("code-block.css")
    assert "@scope (.code-block)" in css, "code-block.css should use @scope to limit token overrides"
    assert "tok-comment" in css, "code-block.css should style .tok-comment"


def test_tokens_layer_used() -> None:
    css = _css_text("tokens.css")
    assert "@layer tokens" in css, "tokens.css must be in the tokens layer"


def test_syntax_theme_includes_pygments_short_aliases() -> None:
    css = _css_text("syntax-theme.css")
    for token in SYNTAX_TOKENS:
        assert f".{token}" in css, f"syntax-theme.css should style .{token}"
