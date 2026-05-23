from __future__ import annotations

from webcompy.ports._server._virtual_dom import VirtualDOMEvent
from webcompy.testing._asgi import create_test_asgi_app, format_html
from webcompy.testing._dom import FakeDOMNode
from webcompy.testing._ports import (
    FakeBrowserDOMPort,
    FakeBrowserFFIPort,
    FakeBrowserHostPort,
)
from webcompy.testing._renderer import TestRenderer, TestRendererResult
from webcompy.testing._scope import (
    create_browser_scope,
    create_server_scope,
    create_test_app,
)

__all__ = [
    "FakeBrowserDOMPort",
    "FakeBrowserFFIPort",
    "FakeBrowserHostPort",
    "FakeDOMNode",
    "TestRenderer",
    "TestRendererResult",
    "VirtualDOMEvent",
    "create_browser_scope",
    "create_server_scope",
    "create_test_app",
    "create_test_asgi_app",
    "format_html",
]
