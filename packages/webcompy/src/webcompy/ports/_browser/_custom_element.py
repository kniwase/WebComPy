from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from webcompy.components._libs import WebComPyComponentException
from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._custom_element import CustomElementBinding, CustomElementPort
from webcompy.ports._dom import DOMNode
from webcompy.utils._environment import ENVIRONMENT

_CONNECTED = 1
_DISCONNECTED = 2
_ATTRIBUTE_CHANGED = 3

_BINDING_PROPERTY = "__webcompyBinding"
_DEFINITION_KEY_PROPERTY = "webcompyDefinitionKey"


def _bridge_class_source(observed_json: str, key_json: str) -> str:
    return (
        "(function(observed, definitionKey){"
        "  var cls = class extends HTMLElement {"
        "    static get observedAttributes() { return observed; }"
        "    connectedCallback() { var b = this.__webcompyBinding; if (b && b.notify) b.notify(1); }"
        "    disconnectedCallback() { var b = this.__webcompyBinding; if (b && b.notify) b.notify(2); }"
        "    attributeChangedCallback(n,o,v) { var b = this.__webcompyBinding; if (b && b.notify) b.notify(3, n, o, v); }"
        "  };"
        "  cls.webcompyDefinitionKey = definitionKey;"
        "  return cls;"
        "})(" + observed_json + ", " + key_json + ")"
    )


class _BrowserCustomElementBinding(CustomElementBinding):
    def __init__(self, node: DOMNode, proxy: Any, ffi: Any, marker: Any) -> None:
        self._node = node
        self._proxy = proxy
        self._ffi = ffi
        self._marker = marker

    def dispose(self) -> None:
        if hasattr(self._proxy, "destroy"):
            self._proxy.destroy()
        if getattr(self._node, _BINDING_PROPERTY, None) == self._marker:
            setattr(self._node, _BINDING_PROPERTY, None)


class BrowserCustomElementPort(CustomElementPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserCustomElementPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser
        self._defined: dict[str, str] = {}

    def ensure_defined(
        self,
        name: str,
        observed_attributes: tuple[str, ...],
        definition_key: str,
    ) -> None:
        if name in self._defined and self._defined[name] == definition_key:
            return
        registry = self._browser.window.customElements
        existing = registry.get(name)
        if existing is not None:
            marker = getattr(existing, _DEFINITION_KEY_PROPERTY, None)
            if marker == definition_key:
                self._defined[name] = definition_key
                return
            raise WebComPyComponentException(f"Custom element '{name}' is already defined with incompatible metadata")
        observed_json = json.dumps(list(observed_attributes))
        key_json = json.dumps(definition_key)
        cls = self._browser.window.eval(_bridge_class_source(observed_json, key_json))
        registry.define(name, cls)
        self._defined[name] = definition_key

    def bind(
        self,
        node: DOMNode,
        *,
        observed_attributes: tuple[str, ...],
        on_connected: Callable[[], None],
        on_disconnected: Callable[[], None],
        on_attribute_changed: Callable[[str, str | None], None],
    ) -> CustomElementBinding:
        ffi = self._browser.pyscript.ffi

        def notify(*args: Any) -> None:
            event_type = int(args[0])
            if event_type == _CONNECTED:
                on_connected()
            elif event_type == _DISCONNECTED:
                on_disconnected()
            elif event_type == _ATTRIBUTE_CHANGED:
                name = str(args[1])
                new_value = None if ffi.is_none(args[3]) else str(args[3])
                on_attribute_changed(name, new_value)

        proxy = ffi.create_proxy(notify)
        binding_marker = ffi.to_js({"notify": proxy})
        setattr(node, _BINDING_PROPERTY, binding_marker)
        return _BrowserCustomElementBinding(node, proxy, ffi, binding_marker)

    def is_document_connected(self, node: DOMNode) -> bool:
        return bool(node.isConnected)
