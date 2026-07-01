from __future__ import annotations

import re
from pathlib import Path

STYLES_DIR = Path(__file__).resolve().parent.parent / "packages" / "webcompy" / "src" / "webcompy" / "ui" / "_styles"


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
        r"@layer\s+reset,\s*tokens,\s*components,\s*webcompy-scope\s*;",
        css,
    ), "index.css must declare '@layer reset, tokens, components, webcompy-scope;' once"


def test_index_css_does_not_import_tokens_dark() -> None:
    css = _css_text("index.css")
    assert "tokens-dark" not in css, (
        "tokens-dark.css was removed; dark theme tokens are now applied "
        "via app.append_style(reactive_block(...)) at runtime"
    )


def test_tokens_light_defined_for_every_color_token() -> None:
    css = _css_text("tokens.css")
    for token in COLOR_TOKENS + SYNTAX_TOKENS:
        assert f"--{token}" in css, f"Light theme missing token --{token}"


def test_dark_tokens_defined_in_python() -> None:
    """Dark theme tokens are now in Python (webcompy/ui/theme/_tokens.py)
    so the reactive style system can inject them at runtime (unlayered,
    with !important on individual declarations to win over static tokens).
    """
    from webcompy.ui.theme._tokens import DARK_TOKENS

    for token in COLOR_TOKENS + SYNTAX_TOKENS:
        assert f"--{token}" in DARK_TOKENS, f"Dark theme missing token --{token} in webcompy/ui/theme/_tokens.py"


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


def test_tokens_dark_css_removed_from_styles_registry() -> None:
    """``tokens-dark.css`` was removed when dark tokens were moved to
    Python in the reactive theme migration. The ``_STYLES_FILES`` allowlist
    must no longer mention it, and the file must not exist on disk.
    """
    from webcompy.ui._styles import _STYLES_FILES, get_styles_file

    assert "tokens-dark.css" not in _STYLES_FILES
    assert get_styles_file("tokens-dark.css") is None
    assert not (STYLES_DIR / "tokens-dark.css").exists()
