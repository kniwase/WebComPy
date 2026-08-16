from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from webcompy import logging
from webcompy.ports._keys import DOM_PORT_KEY, HOST_PORT_KEY
from webcompy.signal._composable import _get_active_component_context
from webcompy.signal._readonly import ReadonlySignal, use_readonly_signal

T = TypeVar("T")

_EVENT_OUTSIDE_SETUP_MSG = "webcompy events: event composable called outside component setup; no listener attached"


def _identity(value: T) -> T:
    return value


def _register_destroy_cleanup(cleanup: Callable[[], None]) -> None:
    from webcompy.components._hooks import _register_before_destroy_chained

    _register_before_destroy_chained(cleanup)


def _build(
    event_type: str,
    initial: T,
    transform: Callable[[Any], T] | None,
    attach: Callable[[str, Callable[[Any], None]], Callable[[], None]],
) -> tuple[ReadonlySignal[T], Callable[[T], T]]:
    view, update = use_readonly_signal(initial)
    mapper = _identity if transform is None else transform

    def _handler(raw: Any) -> None:
        try:
            value = mapper(raw)
        except Exception as err:
            logging.warning(f"webcompy events: transform for {event_type!r} failed; signal unchanged: {err}")
            return
        update(value)

    _register_destroy_cleanup(attach(event_type, _handler))
    return view, update


def _use_event(
    event_type: str,
    initial: T,
    transform: Callable[[Any], T] | None,
    port_key: object,
    attach: Callable[[Any, str, Callable[[Any], None]], Callable[[], None]],
) -> tuple[ReadonlySignal[T], Callable[[T], T]]:
    ctx = _get_active_component_context()
    if ctx is None:
        warnings.warn(_EVENT_OUTSIDE_SETUP_MSG, UserWarning, stacklevel=3)
        return use_readonly_signal(initial)
    from webcompy.di import inject

    port = inject(port_key, default=None)
    if port is None:
        return use_readonly_signal(initial)
    return _build(event_type, initial, transform, lambda ev, handler: attach(port, ev, handler))


def use_window_event(
    event_type: str,
    initial: T,
    *,
    transform: Callable[[Any], T] | None = None,
) -> tuple[ReadonlySignal[T], Callable[[T], T]]:
    """Bridge a window state event into a read-only signal.

    Inside component setup with a resolvable ``HostPort``, a listener is
    attached via ``HostPort.add_window_event_listener`` and removed on
    component destroy. Outside component setup a ``UserWarning`` is emitted
    and nothing is attached; a missing port (or the server ``ServerHostPort``
    no-op) keeps the signal at ``initial``.
    """
    return _use_event(
        event_type,
        initial,
        transform,
        HOST_PORT_KEY,
        lambda port, ev, handler: port.add_window_event_listener(ev, handler),
    )


def use_document_event(
    event_type: str,
    initial: T,
    *,
    transform: Callable[[Any], T] | None = None,
) -> tuple[ReadonlySignal[T], Callable[[T], T]]:
    """Bridge a document state event into a read-only signal.

    Same semantics as :func:`use_window_event` but the listener is attached
    via ``DOMPort.add_document_event_listener``.
    """
    return _use_event(
        event_type,
        initial,
        transform,
        DOM_PORT_KEY,
        lambda port, ev, handler: port.add_document_event_listener(ev, handler),
    )


if TYPE_CHECKING:
    _check_window: tuple[ReadonlySignal[int], Callable[[int], int]] = use_window_event("resize", 0)
    _check_document: tuple[ReadonlySignal[str], Callable[[str], str]] = use_document_event(
        "visibilitychange", "visible", transform=lambda e: str(e.type)
    )
