from __future__ import annotations

from webcompy.components._generator import ComponentGenerator


def _make_generator(selector: str, style: dict) -> ComponentGenerator:
    def _def(_ctx):
        return None

    gen = ComponentGenerator("TestComponent", _def)
    gen.scoped_style = {selector: style}  # type: ignore[assignment]
    return gen


def test_scoped_style_wraps_in_webcompy_scope_layer() -> None:
    gen = _make_generator(".btn", {"color": "red"})
    out = gen.scoped_style
    assert out.startswith("@layer webcompy-scope {")
    assert out.rstrip().endswith("}")
    assert ".btn[webcompy-cid-" in out
    assert "color: red" in out


def test_scoped_style_empty_returns_empty_string() -> None:
    def _def(_ctx):
        return None

    gen = ComponentGenerator("EmptyComponent", _def)
    assert gen.scoped_style == ""


def test_scoped_style_includes_cid_in_selectors() -> None:
    gen = _make_generator(".x", {"font-size": "12px"})
    out = gen.scoped_style
    assert "webcompy-cid-" in out
