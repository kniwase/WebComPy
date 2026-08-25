"""Realtime connection composables: Server-Sent Events and WebSocket messaging."""

from webcompy.realtime._registry import CloseInfo, ConnectionState
from webcompy.realtime._sse import EventSourceHandle, SSEvent, use_event_source
from webcompy.realtime._typed import TypedWebSocketHandle, register_realtime_type_handler
from webcompy.realtime._ws import WebSocketHandle, use_websocket

__all__ = [
    "CloseInfo",
    "ConnectionState",
    "EventSourceHandle",
    "SSEvent",
    "TypedWebSocketHandle",
    "WebSocketHandle",
    "register_realtime_type_handler",
    "use_event_source",
    "use_websocket",
]
