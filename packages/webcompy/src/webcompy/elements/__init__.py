from webcompy.elements.types._refference import DomNodeRef  # noqa: I001
from webcompy.elements import html, typealias, types
from webcompy.elements._dom_objs import DOMEvent, DOMNode
from webcompy.elements._head import HeadElement
from webcompy.elements.generators import (
    break_line,
    client_only,
    create_element,
    event,
    noderef,
    raw_html,
    repeat,
    suspense,
    switch,
    text,
)
from webcompy.elements.types._client_only import ClientOnlyElement
from webcompy.elements.types._error_boundary import ErrorBoundaryElement
from webcompy.elements.types._suspense import SuspenseElement
from webcompy.elements.types._teleport import TeleportElement
from webcompy.elements.types._transition import TransitionElement

ClientOnly = ClientOnlyElement
ErrorBoundary = ErrorBoundaryElement
Suspense = SuspenseElement
Teleport = TeleportElement
Transition = TransitionElement

__all__ = [
    "ClientOnly",
    "DOMEvent",
    "DOMNode",
    "DomNodeRef",
    "ErrorBoundary",
    "HeadElement",
    "Suspense",
    "Teleport",
    "Transition",
    "break_line",
    "client_only",
    "create_element",
    "event",
    "html",
    "noderef",
    "raw_html",
    "repeat",
    "suspense",
    "switch",
    "text",
    "typealias",
    "types",
]
