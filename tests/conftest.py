from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from webcompy.ports._history import HistoryPort
from webcompy.testing import (
    FakeBrowserDOMPort,
    FakeBrowserFFIPort,
    FakeBrowserHostPort,
    FakeDOMNode,
)


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


class MockHistoryPort(HistoryPort):
    def __init__(self, *, mode: str = "history", initial_path: str = "/"):
        super().__init__(initial_path, mode=mode)  # type: ignore[arg-type]

    def current_search(self) -> str:
        return ""

    def history_state(self) -> object | None:
        return self._state

    def refresh_from_window(self) -> None:
        pass


@pytest.fixture
def fake_browser(monkeypatch):
    browser = FakeBrowserModule()
    from webcompy.ports._browser import _raw

    monkeypatch.setattr(_raw, "browser", browser)
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


@pytest.fixture
def fake_browser_full(monkeypatch, reset_di_scope):
    import importlib

    from webcompy.di._scope import DIScope, _active_di_scope
    from webcompy.ports._keys import DOM_PORT_KEY, FFI_PORT_KEY, HOST_PORT_KEY

    modules_with_env: list[str] = []
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


@pytest.fixture
def server_di_scope():
    from webcompy.di._scope import DIScope, _active_di_scope
    from webcompy.ports._keys import DOM_PORT_KEY, FFI_PORT_KEY, HOST_PORT_KEY
    from webcompy.ports._server._dom import ServerDOMPort
    from webcompy.ports._server._ffi import ServerFFIPort
    from webcompy.ports._server._host import ServerHostPort

    scope = DIScope()
    scope.provide(DOM_PORT_KEY, ServerDOMPort())
    scope.provide(HOST_PORT_KEY, ServerHostPort())
    scope.provide(FFI_PORT_KEY, ServerFFIPort())
    token = _active_di_scope.set(scope)
    yield scope
    _active_di_scope.reset(token)
