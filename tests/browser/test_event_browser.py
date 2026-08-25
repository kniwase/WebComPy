"""Real FFI proxy lifecycle and DOM event dispatch.

Top-level imports must stay CPython-importable: browser-only modules are
imported inside function bodies (CPython-importability invariant).
"""


def test_event_dispatch_and_proxy_destroy(app, dom_root):
    from webcompy.di import inject
    from webcompy.ports._keys import DOM_PORT_KEY, FFI_PORT_KEY

    dom_port = inject(DOM_PORT_KEY)
    ffi_port = inject(FFI_PORT_KEY)

    clicks = []
    button = dom_port.create_element("button")
    handler_proxy = ffi_port.create_proxy(lambda event: clicks.append(1))
    button.addEventListener("click", handler_proxy)
    dom_root.appendChild(button)

    button.dispatchEvent(dom_port.create_event("click", bubbles=True))

    assert len(clicks) == 1

    ffi_port.destroy_proxy(handler_proxy)


def test_document_event_listener_cleanup(app, dom_root):
    import js

    from webcompy.di import inject
    from webcompy.ports._keys import DOM_PORT_KEY

    clicks = []
    remove = inject(DOM_PORT_KEY).add_document_event_listener("click", lambda event: clicks.append(1))

    js.document.body.click()
    assert len(clicks) == 1

    remove()
    js.document.body.click()
    assert len(clicks) == 1
