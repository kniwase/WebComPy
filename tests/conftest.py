from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class FakeDOMNode:
    def __init__(self, tag: str = "div", text_content: str | None = None):
        self.__nodeName = tag.upper() if tag != "#text" else "#text"
        self.__childNodes: list[FakeDOMNode] = []
        self.__textContent = text_content or ""
        self.__parentNode: FakeDOMNode | None = None
        self.__attrs: dict[str, str] = {}
        self.__event_listeners: dict[str, list] = {}
        self.__children: list[FakeDOMNode] = []
        self.__webcompy_node__ = True
        self.__webcompy_prerendered_node__ = False
        self.textContent_write_count = 0
        self.setAttribute_count = 0

    @property
    def childNodes(self):
        class ChildNodeList:
            def __init__(self, nodes):
                self._nodes = nodes

            @property
            def length(self):
                return len(self._nodes)

            def __getitem__(self, idx):
                if idx < 0:
                    return self._nodes[idx]
                return self._nodes[idx]

            def __len__(self):
                return len(self._nodes)

        return ChildNodeList(self.__childNodes)

    @property
    def nodeName(self):
        return self.__nodeName

    @property
    def textContent(self):
        return self.__textContent

    @textContent.setter
    def textContent(self, value):
        self.__textContent = value
        self.textContent_write_count += 1

    def appendChild(self, child):
        self.__childNodes.append(child)
        child.__parentNode = self

    def insertBefore(self, new_node, ref_node):
        idx = self.__childNodes.index(ref_node)
        self.__childNodes.insert(idx, new_node)
        new_node.__parentNode = self

    def replaceChild(self, new_node, old_node):
        idx = self.__childNodes.index(old_node)
        self.__childNodes[idx] = new_node
        new_node.__parentNode = self
        old_node.__parentNode = None

    @property
    def parentNode(self):
        return self.__parentNode

    def remove(self):
        if self.__parentNode and self in self.__parentNode.__childNodes:
            self.__parentNode.__childNodes.remove(self)
        self.__parentNode = None

    def setAttribute(self, name, value):
        self.__attrs[name] = value
        self.setAttribute_count += 1

    def removeAttribute(self, name):
        self.__attrs.pop(name, None)

    def getAttributeNames(self):
        return list(self.__attrs.keys())

    def getAttribute(self, name):
        return self.__attrs.get(name)

    def hasAttribute(self, name):
        return name in self.__attrs

    def addEventListener(self, event, handler, *args):
        self.__event_listeners.setdefault(event, []).append(handler)

    def removeEventListener(self, event, handler, *args):
        if event in self.__event_listeners:
            self.__event_listeners[event] = [h for h in self.__event_listeners[event] if h is not handler]

    def __setattr__(self, name, value):
        if name.startswith("_FakeDOMNode__") or name in (
            "__webcompy_node__",
            "__webcompy_prerendered_node__",
        ):
            object.__setattr__(self, name, value)
        else:
            try:
                object.__getattribute__(self, name)
                object.__setattr__(self, name, value)
            except AttributeError:
                object.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name.startswith("_FakeDOMNode__"):
            raise AttributeError(name)
        return object.__getattribute__(self, name)


class FakePyScriptFfi:
    def create_proxy(self, func):
        proxy = MagicMock(side_effect=func)
        proxy.destroy = MagicMock()
        return proxy

    def is_none(self, value):
        return value is None

    def to_js(self, value, **kw):
        return value

    def assign(self, source, *args):
        for arg in args:
            source.update(arg)
        return source


class FakePyScript:
    def __init__(self):
        self.ffi = FakePyScriptFfi()


class FakeConsole:
    def __init__(self):
        self.log = MagicMock()
        self.debug = MagicMock()
        self.info = MagicMock()
        self.warn = MagicMock()
        self.error = MagicMock()


class FakeLocation:
    def __init__(self):
        self.pathname = "/"
        self.search = ""
        self.hash = ""


class FakeHistory:
    def __init__(self):
        self._state = None
        self.pushState = MagicMock()

    @property
    def state(self):
        return self._state


class FakeWindow:
    def __init__(self):
        self.location = FakeLocation()
        self.history = FakeHistory()
        self._listeners: dict[str, list] = {}

    def addEventListener(self, event, handler, *args):
        self._listeners.setdefault(event, []).append(handler)

    def removeEventListener(self, event, handler, *args):
        if event in self._listeners:
            self._listeners[event] = [h for h in self._listeners[event] if h is not handler]


class FakeDocument:
    def __init__(self):
        self._elements: dict[str, FakeDOMNode] = {}
        self.title = ""

    def createElement(self, tag):
        return FakeDOMNode(tag)

    def createTextNode(self, text):
        return FakeDOMNode("#text", text_content=text)

    def getElementById(self, id_str):
        return self._elements.get(id_str)


class FakeDOMEvent:
    def __init__(self, href="/"):
        self.preventDefault = MagicMock()
        self.currentTarget = MagicMock()
        self.currentTarget.getAttribute = MagicMock(return_value=href)


class FakeFetchResponse:
    def __init__(self, text="", headers=None, status=200, status_text="OK", ok=True):
        self._text = text
        self._headers = headers or {}
        self._status = status
        self._status_text = status_text
        self._ok = ok

    async def text(self):
        return self._text

    @property
    def headers(self):
        return self._headers

    @property
    def status(self):
        return self._status

    @property
    def statusText(self):
        return self._status_text

    @property
    def ok(self):
        return self._ok


class FakeFormData:
    def __init__(self):
        self._data = {}

    def set(self, key, value):
        self._data[key] = value

    @classmethod
    def new(cls):
        return cls()


class FakeBrowserModule:
    def __init__(self):
        self.document = FakeDocument()
        self.window = FakeWindow()
        self.pyscript = FakePyScript()
        self.console = FakeConsole()
        self.fetch = MagicMock()
        self.FormData = FakeFormData

    def __getattr__(self, name):
        return MagicMock()

    def __bool__(self):
        return True


@pytest.fixture
def fake_browser(monkeypatch):
    browser = FakeBrowserModule()
    from webcompy._browser import _modules

    monkeypatch.setattr(_modules, "browser", browser)
    return browser


@pytest.fixture
def fake_document(fake_browser):
    return fake_browser.document


@pytest.fixture(autouse=True)
def reset_di_scope():
    from webcompy.components._generator import _unregistered_generators

    saved = _unregistered_generators[:]
    _unregistered_generators.clear()
    yield
    _unregistered_generators.clear()
    _unregistered_generators.extend(saved)


class FakeBrowserDOMPort:
    def create_element(self, tag: str):
        return FakeDOMNode(tag)

    def create_text_node(self, text: str):
        return FakeDOMNode("#text", text_content=text)

    def add_document_event_listener(self, event_type, handler):
        return lambda: None


class FakeBrowserHostPort:
    def schedule_macro_task(self, callback):
        pass

    def create_js_global_getter(self, name, *, wrapper=None, default=None):
        def _getter():
            if wrapper is not None:
                return wrapper(None)
            return default

        return _getter


class FakeBrowserFFIPort:
    def create_proxy(self, func):
        proxy = MagicMock(side_effect=func)
        proxy.destroy = MagicMock()
        return proxy

    def destroy_proxy(self, proxy):
        if hasattr(proxy, "destroy"):
            proxy.destroy()

    def is_none(self, value):
        return value is None


@pytest.fixture
def fake_browser_full(monkeypatch, reset_di_scope):
    import importlib

    from webcompy.di._scope import DIScope, _active_di_scope
    from webcompy.ports._keys import DOM_PORT_KEY, FFI_PORT_KEY, HOST_PORT_KEY

    modules_with_env = [
        "webcompy.elements.types._element",
        "webcompy.elements.types._abstract",
        "webcompy.elements.types._text",
        "webcompy.elements.types._switch",
        "webcompy.elements.types._dynamic",
        "webcompy.elements.types._repeat",
    ]
    for mod_name in modules_with_env:
        mod = importlib.import_module(mod_name)
        monkeypatch.setattr(mod, "ENVIRONMENT", "pyscript")

    dom_port = FakeBrowserDOMPort()
    host_port = FakeBrowserHostPort()
    ffi_port = FakeBrowserFFIPort()

    scope = DIScope()
    scope.provide(DOM_PORT_KEY, dom_port)
    scope.provide(HOST_PORT_KEY, host_port)
    scope.provide(FFI_PORT_KEY, ffi_port)

    prev_token = _active_di_scope.set(scope)
    yield dom_port, host_port, ffi_port
    _active_di_scope.reset(prev_token)
