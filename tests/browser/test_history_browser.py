"""Browser-tier tests for BrowserHistoryPort JsProxy history state handling.

Top-level imports must stay CPython-importable: browser-only modules are
imported inside function bodies (CPython-importability invariant).
"""


def test_browser_history_port_converts_js_proxy_state(app, dom_root):
    import js
    from pyodide.ffi import to_js

    from webcompy.ports._browser._history import BrowserHistoryPort

    port = BrowserHistoryPort(mode="hash")
    prev_href = str(js.window.location.href)
    received: list[tuple[str, dict | None]] = []
    port.set_navigation_callback(lambda p, s: received.append((p, s)))
    try:
        js_state = to_js({"from_js": 42, "tag": "ok"}, dict_converter=js.Object.fromEntries)
        js.window.history.pushState(js_state, "", "#/history-probe/")
        port.refresh_from_window()
        assert port.value == "/history-probe/"
        assert port.state == {"from_js": 42, "tag": "ok"}

        port._on_popstate(None)
        assert received == [("/history-probe/", {"from_js": 42, "tag": "ok"})]

        js.window.history.replaceState("non-object-state", "", "#/history-scalar/")
        port.refresh_from_window()
        assert port.value == "/history-scalar/"
        assert port.state is None
    finally:
        js.window.removeEventListener("popstate", port._popstate_handler_proxy)
        port._popstate_handler_proxy.destroy()
        js.window.history.replaceState(None, "", prev_href)
