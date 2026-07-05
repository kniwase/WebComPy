from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING, Any

from webcompy.components._component import Component
from webcompy.di import inject
from webcompy.hydration._codec import encode
from webcompy.hydration._payload import TransferAsyncResultEntry, TransferFetchEntry, TransferPayload
from webcompy.ports._keys import FETCH_PORT_KEY

if TYPE_CHECKING:
    from webcompy.aio._async_result import AsyncResult
    from webcompy.app._root_component import AppDocumentRoot

_logger = getLogger(__name__)


def collect_transfer_data(root: AppDocumentRoot) -> TransferPayload:
    from webcompy.aio._async_result import AsyncState

    fetches: dict[str, TransferFetchEntry] = {}
    async_results: dict[str, TransferAsyncResultEntry] = {}

    fetch_port = inject(FETCH_PORT_KEY, default=None)
    if fetch_port is not None and hasattr(fetch_port, "get_transfer_data"):
        fetches = fetch_port.get_transfer_data()

    for component, async_instances in _walk_component_async_results(root):
        component_id = component._property.get("component_id", "")
        for ar in async_instances:
            if ar._state.value == AsyncState.SUCCESS:
                async_results[component_id] = TransferAsyncResultEntry(
                    state="success",
                    data=encode(ar._data.value),
                )

    return TransferPayload(
        __webcompy_transfer_version__=1,
        fetches=fetches,
        async_results=async_results,
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
