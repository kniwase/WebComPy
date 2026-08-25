"""Cross-test DOM isolation of non-chrome body children.

The first test deliberately appends a non-DIV element directly to
``document.body``; the following test asserts the isolation sweep removed
it, guarding the body-clearing half of the per-test isolation protocol.

JS null results (e.g. a ``querySelector`` miss) are falsy ``JsNull``
proxies under PyScript, never Python ``None`` — assertions must use
truthiness, not identity comparison.

Top-level imports must stay CPython-importable: browser-only modules are
imported inside function bodies (CPython-importability invariant).
"""


def test_00_append_span_directly_to_body(app, dom_root):
    import js

    span = js.document.createElement("span")
    span.setAttribute("data-webcompy-isolation-probe", "")
    span.textContent = "leftover probe"
    js.document.body.appendChild(span)

    assert js.document.body.querySelector("[data-webcompy-isolation-probe]")


def test_01_body_has_no_leftovers(app, dom_root):
    import js

    names = [child.nodeName for child in js.document.body.childNodes]
    assert "SPAN" not in names, names

    leftover = js.document.querySelector("[data-webcompy-isolation-probe]")
    assert not leftover, f"probe survived isolation: {names}"
