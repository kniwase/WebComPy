from __future__ import annotations

from webcompy_server.ports import VirtualDOMEvent
from webcompy_testing._app import mock_app_run
from webcompy_testing._asgi import (
    create_test_asgi_app,
    format_html,
)
from webcompy_testing._asgi import (
    render_app_html_sync as render_app_html,
)
from webcompy_testing._dom import FakeDOMNode
from webcompy_testing._ports import (
    FakeBrowserDOMPort,
    FakeBrowserFFIPort,
    FakeBrowserHostPort,
    FakeFetchPort,
)
from webcompy_testing._renderer import TestRenderer, TestRendererResult
from webcompy_testing._scope import create_test_app
from webcompy_testing._utils import run_sync

__all__ = [
    "FakeBrowserDOMPort",
    "FakeBrowserFFIPort",
    "FakeBrowserHostPort",
    "FakeDOMNode",
    "FakeFetchPort",
    "TestRenderer",
    "TestRendererResult",
    "VirtualDOMEvent",
    "create_test_app",
    "create_test_asgi_app",
    "format_html",
    "mock_app_run",
    "render_app_html",
    "run_sync",
]
