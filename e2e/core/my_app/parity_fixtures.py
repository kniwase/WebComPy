from __future__ import annotations

from webcompy.elements.types._element import Element
from webcompy.elements.types._text import TextElement
from webcompy.template import render_template

PARITY_TEMPLATES: dict[str, str] = {
    "textarea_markup": "<div><textarea><b>x</b></textarea></div>",
    "title_markup": "<div><title><b>y</b></title></div>",
    "pre_plain": "<pre>  a\n  b</pre>",
    "charref_decoded": "<p>&lt;tag&gt; &amp; &#65;</p>",
    "plaintext_unclosed": "<div><plaintext><b>z</b>",
}


def serialize_tree(node: object) -> str:
    if isinstance(node, TextElement):
        return f"#text({node._get_text()!r})"
    if isinstance(node, Element):
        attrs = ",".join(f"{k}={v!r}" for k, v in sorted(node._attrs.items()))
        children = ";".join(serialize_tree(c) for c in node._children)
        return f"{node._tag_name}[{attrs}]({children})"
    msg = f"Unexpected node type: {type(node).__name__}"
    raise TypeError(msg)


def compute_parity_results() -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for name, source in PARITY_TEMPLATES.items():
        try:
            results[name] = ["tree", serialize_tree(render_template(source, {}))]
        except Exception as exc:
            results[name] = ["error", f"{type(exc).__name__}: {exc}"]
    return results
