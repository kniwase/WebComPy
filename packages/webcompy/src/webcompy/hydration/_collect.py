"""Collection of transfer data from the server-rendered component tree."""

from __future__ import annotations

import base64
from logging import getLogger
from typing import TYPE_CHECKING, Any

from webcompy.components._component import Component
from webcompy.di import inject
from webcompy.hydration._payload import (
    CURRENT_TRANSFER_VERSION,
    TransferAsyncResultEntry,
    TransferFetchEntry,
    TransferPayload,
)
from webcompy.ports._keys import FETCH_PORT_KEY, RESOURCE_PORT_KEY
from webcompy.signal import Computed, SignalBase

if TYPE_CHECKING:
    from webcompy.aio._async_result import AsyncResult
    from webcompy.app._root_component import AppDocumentRoot

_logger = getLogger(__name__)


def collect_transfer_data(root: AppDocumentRoot) -> TransferPayload:
    from webcompy.aio._async_result import AsyncState

    fetches: dict[str, TransferFetchEntry] = {}
    async_results: dict[str, TransferAsyncResultEntry] = {}
    signals: dict[str, dict[str, Any]] = {}
    resources: dict[str, str] = {}

    fetch_port = inject(FETCH_PORT_KEY, default=None)
    if fetch_port is not None and hasattr(fetch_port, "get_transfer_data"):
        fetches = fetch_port.get_transfer_data()

    resource_port = inject(RESOURCE_PORT_KEY, default=None)
    if resource_port is not None and hasattr(resource_port, "get_recorded_resources"):
        recorded = resource_port.get_recorded_resources()
        resources = {path: base64.b64encode(content).decode("ascii") for path, content in recorded.items()}

    full_text = getattr(getattr(root, "_app", None), "_ssg_full_text_resources", None)
    if full_text:
        for path, content in full_text.items():
            resources.setdefault(path, base64.b64encode(content).decode("ascii"))

    for component, async_instances in _walk_component_async_results(root):
        component_id = component._property.get("transfer_id") or component._property.get("component_id", "")
        for ar in async_instances:
            if not getattr(ar, "_transferable", True):
                continue
            if ar._state.value == AsyncState.SUCCESS:
                async_results[component_id] = TransferAsyncResultEntry(
                    state="success",
                    data=ar._data.value,
                )

    for component in _walk_components(root):
        component_signals = _collect_component_signals(component)
        if component_signals:
            component_id = component._property.get("transfer_id") or component._property.get("component_id", "")
            if component_id:
                signals[component_id] = component_signals

    return TransferPayload(
        __webcompy_transfer_version__=CURRENT_TRANSFER_VERSION,
        fetches=fetches,
        async_results=async_results,
        signals=signals,
        resources=resources,
    )


def _walk_component_async_results(root: Any):
    from webcompy.components._component import Component

    def _walk(element: Any):
        if isinstance(element, Component):
            async_instances = _find_async_results_in_component(element)
            if async_instances:
                yield element, async_instances
        if hasattr(element, "_children") and isinstance(element._children, (list, tuple)):
            for child in element._children:
                yield from _walk(child)

    yield from _walk(root)


def _find_async_results_in_component(component: Component) -> list[AsyncResult]:
    return list(component._async_results)


def _walk_components(root: Any):
    from webcompy.components._component import Component

    def _walk(element: Any):
        if isinstance(element, Component):
            yield element
        if hasattr(element, "_children") and isinstance(element._children, (list, tuple)):
            for child in element._children:
                yield from _walk(child)

    yield from _walk(root)


def _collect_component_signals(component: Component) -> dict[str, Any]:
    members = getattr(component, "__signal_members__", None)
    if not members:
        return {}
    collected: dict[str, Any] = {}
    for attr_name, signal in members.items():
        if isinstance(signal, Computed):
            continue
        if not isinstance(signal, SignalBase):
            continue
        collected[attr_name] = signal._value
    return collected
