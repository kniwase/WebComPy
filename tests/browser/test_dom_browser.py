"""Real-port DOM manipulation validated against the live document.

Top-level imports must stay CPython-importable: browser-only modules are
imported inside function bodies (CPython-importability invariant).
"""


def test_create_real_div(app, dom_root):
    from webcompy.di import inject
    from webcompy.ports._keys import DOM_PORT_KEY

    port = inject(DOM_PORT_KEY)
    element = port.create_element("div")
    element.setAttribute("data-wc-browser-test", "ok")
    element.textContent = "hello browser tier"
    dom_root.appendChild(element)

    import js

    found = js.document.querySelector("[data-wc-browser-test='ok']")
    assert found is not None
    assert str(found.textContent) == "hello browser tier"


def test_create_text_node_and_query_selector(app, dom_root):
    from webcompy.di import inject
    from webcompy.ports._keys import DOM_PORT_KEY

    port = inject(DOM_PORT_KEY)
    parent = port.create_element("section")
    text = port.create_text_node("nested")
    parent.appendChild(text)
    dom_root.appendChild(parent)

    assert dom_root.querySelector("section") is not None
    assert dom_root.textContent == "nested"
