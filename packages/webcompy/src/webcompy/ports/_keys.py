"""DI injection keys for the WebComPy port implementations."""

from webcompy.di import InjectKey
from webcompy.ports._async_scheduler import AsyncSchedulerPort
from webcompy.ports._cookie import CookiePort
from webcompy.ports._custom_element import CustomElementPort
from webcompy.ports._dom import DOMPort
from webcompy.ports._event_source import EventSourcePort
from webcompy.ports._fetch import FetchPort
from webcompy.ports._ffi import FFIPort
from webcompy.ports._history import HistoryPort
from webcompy.ports._host import HostPort
from webcompy.ports._markdown import MarkdownPort
from webcompy.ports._media_query import MediaQueryPort
from webcompy.ports._middleware import FetchMiddlewareRegistry
from webcompy.ports._resource import ResourcePort
from webcompy.ports._transition import TransitionPort
from webcompy.ports._websocket import WebSocketPort

DOM_PORT_KEY = InjectKey[DOMPort]("webcompy-port-dom")
"""Injection key for the ``DOMPort`` implementation."""
FFI_PORT_KEY = InjectKey[FFIPort]("webcompy-port-ffi")
"""Injection key for the ``FFIPort`` implementation."""
FETCH_PORT_KEY = InjectKey[FetchPort]("webcompy-port-fetch")
"""Injection key for the ``FetchPort`` implementation."""
COOKIE_PORT_KEY = InjectKey[CookiePort]("webcompy-port-cookie")
"""Injection key for the ``CookiePort`` implementation."""
HISTORY_PORT_KEY = InjectKey[HistoryPort]("webcompy-port-history")
"""Injection key for the ``HistoryPort`` implementation."""
HOST_PORT_KEY = InjectKey[HostPort]("webcompy-port-host")
"""Injection key for the ``HostPort`` implementation."""
MARKDOWN_PORT_KEY = InjectKey[MarkdownPort]("webcompy-port-markdown")
"""Injection key for the ``MarkdownPort`` implementation."""
MEDIA_QUERY_PORT_KEY = InjectKey[MediaQueryPort]("webcompy-port-media-query")
"""Injection key for the ``MediaQueryPort`` implementation."""
ASYNC_SCHEDULER_PORT_KEY = InjectKey[AsyncSchedulerPort]("webcompy-port-async-scheduler")
"""Injection key for the ``AsyncSchedulerPort`` implementation."""
RESOURCE_PORT_KEY = InjectKey[ResourcePort]("webcompy-port-resource")
"""Injection key for the ``ResourcePort`` implementation."""
CUSTOM_ELEMENT_PORT_KEY = InjectKey[CustomElementPort]("webcompy-port-custom-element")
"""Injection key for the ``CustomElementPort`` implementation."""
EVENT_SOURCE_PORT_KEY = InjectKey[EventSourcePort]("webcompy-port-event-source")
"""Injection key for the ``EventSourcePort`` implementation."""
TRANSITION_PORT_KEY = InjectKey[TransitionPort]("webcompy-port-transition")
"""Injection key for the ``TransitionPort`` implementation."""
WEBSOCKET_PORT_KEY = InjectKey[WebSocketPort]("webcompy-port-websocket")
"""Injection key for the ``WebSocketPort`` implementation."""
FETCH_MIDDLEWARE_KEY = InjectKey[FetchMiddlewareRegistry]("webcompy-fetch-middleware")
"""Injection key for the per-context ``FetchMiddlewareRegistry``."""
