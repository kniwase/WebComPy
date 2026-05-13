from webcompy.di import InjectKey
from webcompy.ports._cookie import CookiePort
from webcompy.ports._dom import DOMPort
from webcompy.ports._fetch import FetchPort
from webcompy.ports._ffi import FFIPort
from webcompy.ports._history import HistoryPort

DOM_PORT_KEY = InjectKey[DOMPort]("webcompy-port-dom")
FFI_PORT_KEY = InjectKey[FFIPort]("webcompy-port-ffi")
FETCH_PORT_KEY = InjectKey[FetchPort]("webcompy-port-fetch")
COOKIE_PORT_KEY = InjectKey[CookiePort]("webcompy-port-cookie")
HISTORY_PORT_KEY = InjectKey[HistoryPort]("webcompy-port-history")
