"""Regression test for the timing bug where HYDRATION_SIGNAL_DATA_KEY was provided
AFTER the root component's setup function had already been called.

The fix moved the hydration data loading into BrowserRenderContext.__init__
(via _register_ports), which runs BEFORE any component instantiation.
This test verifies the ordering by inspecting the BrowserRenderContext
source code directly and by using a simplified unit test on the
_load_hydration_payload method.
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import MagicMock

from webcompy.di._keys import HYDRATION_DATA_KEY, HYDRATION_SIGNAL_DATA_KEY


class _FakeElement:
    def __init__(self, content: str) -> None:
        self._content = content
        self.textContent = content

    def remove(self) -> None:
        pass


def _make_minimal_payload(component_id: str, key: str, value):
    return {
        "__webcompy_transfer_version__": 2,
        "fetches": {},
        "async_results": {},
        "signals": {component_id: {key: value}},
    }


def _serialize(payload):
    import json

    return json.dumps(payload)


class TestRootComponentHydrationTiming:
    def test__load_hydration_payload_provides_keys_to_di_scope(self):
        from webcompy.app._render_context import BrowserRenderContext

        instance = BrowserRenderContext.__new__(BrowserRenderContext)
        di_scope = MagicMock()
        instance._di_scope = di_scope

        dom_port = MagicMock()
        payload = _make_minimal_payload("cid", "k", 99)
        dom_port.query_selector.return_value = _FakeElement(json.dumps(payload))

        def inject_stub(key, default=None):
            from webcompy.ports._keys import FETCH_PORT_KEY

            if "port-dom" in str(key):
                return dom_port
            if key is FETCH_PORT_KEY:
                return dom_port
            return None

        instance._di_scope.inject.side_effect = inject_stub

        BrowserRenderContext._load_hydration_payload(instance)

        provide_calls = list(di_scope.provide.call_args_list)
        provided_keys = [c.args[0] for c in provide_calls]
        provided_values = {c.args[0]: c.args[1] for c in provide_calls}

        assert HYDRATION_DATA_KEY in provided_keys
        assert provided_values[HYDRATION_DATA_KEY] == payload["async_results"]
        assert HYDRATION_SIGNAL_DATA_KEY in provided_keys
        assert provided_values[HYDRATION_SIGNAL_DATA_KEY] == payload["signals"]

    def test__load_hydration_payload_handles_missing_data_el(self):
        from webcompy.app._render_context import BrowserRenderContext

        instance = BrowserRenderContext.__new__(BrowserRenderContext)
        di_scope = MagicMock()
        instance._di_scope = di_scope

        dom_port = MagicMock()
        dom_port.query_selector.return_value = None

        instance._di_scope.inject.return_value = dom_port

        BrowserRenderContext._load_hydration_payload(instance)

        di_scope.provide.assert_not_called()

    def test_load_hydration_runs_before_root_component_instantiation(self):
        from webcompy.app._render_context import BrowserRenderContext
        from webcompy.components._component import Component

        source = inspect.getsource(BrowserRenderContext.__init__)
        register_ports_idx = source.find("_register_ports")
        assert register_ports_idx > 0

        root_init_idx = source.find("AppDocumentRoot")
        if root_init_idx > 0:
            assert register_ports_idx < root_init_idx, (
                "_register_ports must be called before AppDocumentRoot initialization"
            )

        comp_init_source = inspect.getsource(Component.__init__)
        setup_call_idx = comp_init_source.find("self.__setup")
        assert setup_call_idx > 0
