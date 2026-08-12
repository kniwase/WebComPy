from webcompy.di import InjectKey
from webcompy.ports._async_scheduler import AsyncSchedulerPort
from webcompy.ports._cookie import CookiePort
from webcompy.ports._dom import DOMPort
from webcompy.ports._fetch import FetchPort
from webcompy.ports._ffi import FFIPort
from webcompy.ports._history import HistoryPort
from webcompy.ports._host import HostPort
from webcompy.ports._markdown import MarkdownPort
from webcompy.ports._media_query import MediaQueryPort
from webcompy.ports._resource import ResourcePort
from webcompy.ports._transition import TransitionPort

DOM_PORT_KEY = InjectKey[DOMPort]("webcompy-port-dom")
FFI_PORT_KEY = InjectKey[FFIPort]("webcompy-port-ffi")
FETCH_PORT_KEY = InjectKey[FetchPort]("webcompy-port-fetch")
COOKIE_PORT_KEY = InjectKey[CookiePort]("webcompy-port-cookie")
HISTORY_PORT_KEY = InjectKey[HistoryPort]("webcompy-port-history")
HOST_PORT_KEY = InjectKey[HostPort]("webcompy-port-host")
MARKDOWN_PORT_KEY = InjectKey[MarkdownPort]("webcompy-port-markdown")
MEDIA_QUERY_PORT_KEY = InjectKey[MediaQueryPort]("webcompy-port-media-query")
ASYNC_SCHEDULER_PORT_KEY = InjectKey[AsyncSchedulerPort]("webcompy-port-async-scheduler")
RESOURCE_PORT_KEY = InjectKey[ResourcePort]("webcompy-port-resource")
TRANSITION_PORT_KEY = InjectKey[TransitionPort]("webcompy-port-transition")
