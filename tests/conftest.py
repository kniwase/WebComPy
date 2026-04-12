from __future__ import annotations

import pytest
from unittest.mock import MagicMock


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

    def remove(self):
        if self.__parentNode and self in self.__parentNode.__childNodes:
            self.__parentNode.__childNodes.remove(self)
        self.__parentNode = None

    def setAttribute(self, name, value):
        self.__attrs[name] = value

    def removeAttribute(self, name):
        self.__attrs.pop(name, None)

    def getAttributeNames(self):
        return list(self.__attrs.keys())

    def getAttribute(self, name):
        return self.__attrs.get(name)

    def addEventListener(self, event, handler, *args):
        self.__event_listeners.setdefault(event, []).append(handler)

    def removeEventListener(self, event, handler, *args):
        if event in self.__event_listeners:
            self.__event_listeners[event] = [h for h in self.__event_listeners[event] if h is not handler]

    def __setattr__(self, name, value):
        if name.startswith("_FakeDOMNode__"):
            object.__setattr__(self, name, value)
        elif name in (
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


class FakePyodide:
    def create_proxy(self, func):
        proxy = MagicMock(side_effect=func)
        proxy.destroy = MagicMock()
        return proxy


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

    def to_py(self):
        return self

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
        self.pyodide = FakePyodide()
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
def reset_router_singleton():
    from webcompy.router._router import Router

    Router._instance = None
    yield
    Router._instance = None


@pytest.fixture(autouse=True)
def reset_router_link():
    from webcompy.router._link import TypedRouterLink

    TypedRouterLink._router = None
    yield
    TypedRouterLink._router = None
