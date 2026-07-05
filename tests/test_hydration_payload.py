from __future__ import annotations

import json
from unittest.mock import MagicMock

from webcompy.aio._async_result import AsyncResult, AsyncState
from webcompy.components._component import Component
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.hydration._collect import (
    _find_async_results_in_component,
    _walk_component_async_results,
    collect_transfer_data,
)
from webcompy.hydration._payload import (
    TransferAsyncResultEntry,
    TransferFetchEntry,
    TransferPayload,
    deserialize_payload,
    serialize_payload,
)
from webcompy.ports._keys import FETCH_PORT_KEY


class TestTransferPayload:
    def test_payload_with_fetches_and_async_results(self):
        payload = TransferPayload(
            fetches={
                "/api/data": TransferFetchEntry(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    body='{"key": "value"}',
                ),
            },
            async_results={
                "cmp-1": TransferAsyncResultEntry(
                    state="success",
                    data={"result": 42},
                ),
            },
        )
        serialized = serialize_payload(payload)
        assert isinstance(serialized, str)
        result = deserialize_payload(serialized)
        assert result is not None
        assert result.__webcompy_transfer_version__ == 2
        assert "/api/data" in result.fetches
        assert result.fetches["/api/data"].status_code == 200
        assert result.fetches["/api/data"].body == '{"key": "value"}'
        assert "cmp-1" in result.async_results
        assert result.async_results["cmp-1"].state == "success"
        assert result.async_results["cmp-1"].data == {"result": 42}

    def test_empty_payload(self):
        payload = TransferPayload()
        serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert result.fetches == {}
        assert result.async_results == {}
        assert result.__webcompy_transfer_version__ == 2

    def test_html_escaping_of_special_characters(self):
        payload = TransferPayload(
            async_results={
                "cmp-1": TransferAsyncResultEntry(
                    state="success",
                    data={"html": "<script>alert('xss')</script>", "text": "a & b < c > d"},
                ),
            },
        )
        serialized = serialize_payload(payload)
        assert "&lt;" in serialized or "&gt;" in serialized or "&amp;" in serialized
        result = deserialize_payload(serialized)
        assert result is not None
        data = result.async_results["cmp-1"].data
        assert data["html"] == "<script>alert('xss')</script>"
        assert data["text"] == "a & b < c > d"

    def test_unknown_version_is_rejected(self):
        raw = json.dumps({"__webcompy_transfer_version__": 999, "fetches": {}, "async_results": {}})
        result = deserialize_payload(raw)
        assert result is None

    def test_malformed_json_returns_none(self):
        result = deserialize_payload("not json at all")
        assert result is None

    def test_non_dict_json_returns_none(self):
        result = deserialize_payload("[]")
        assert result is None

    def test_missing_version_field_returns_none(self):
        raw = json.dumps({"fetches": {}, "async_results": {}})
        result = deserialize_payload(raw)
        assert result is None

    def test_payload_with_non_serializable_data_excluded(self):
        class NonSerializable:
            pass

        payload = TransferPayload(
            async_results={
                "cmp-1": TransferAsyncResultEntry(
                    state="success",
                    data={"obj": NonSerializable()},
                ),
            },
        )
        serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert "cmp-1" not in result.async_results

    def test_serialized_is_valid_json(self):
        payload = TransferPayload(
            fetches={"/test": TransferFetchEntry(status_code=200, headers={}, body="ok")},
        )
        serialized = serialize_payload(payload)
        import html as html_module

        unescaped = html_module.unescape(serialized)
        parsed = json.loads(unescaped)
        assert parsed["__webcompy_transfer_version__"] == 2
        assert "/test" in parsed["fetches"]


class TestCollectTransferData:
    def _make_component(self, async_results, component_id="test-cmp"):
        mock = MagicMock(spec=Component)
        mock._async_results = async_results
        mock._children = []
        mock._property = {"component_id": component_id}
        return mock

    def _make_root(self, children):
        root = MagicMock()
        root._children = children
        return root

    def test_find_async_results_from_component_registration(self):
        async def fetch():
            return "data"

        result = AsyncResult(fetch)
        result._state.value = AsyncState.SUCCESS
        result._data.value = "test"

        mock_component = self._make_component([result])
        found = _find_async_results_in_component(mock_component)
        assert len(found) == 1
        assert found[0] is result

    def test_find_async_results_empty_when_empty_list(self):
        mock_component = self._make_component([])
        found = _find_async_results_in_component(mock_component)
        assert found == []

    def test_walk_component_async_results_yields_with_results(self):
        async def fetch():
            return "data"

        result = AsyncResult(fetch)
        result._state.value = AsyncState.SUCCESS
        result._data.value = "test"

        child = self._make_component([result])
        parent = self._make_root([child])

        results = list(_walk_component_async_results(parent))
        assert len(results) == 1
        assert results[0][0] is child
        assert results[0][1] == [result]

    def test_walk_skips_non_component_without_async_results(self):
        elem = MagicMock()
        elem._children = []

        results = list(_walk_component_async_results(elem))
        assert results == []

    def test_collect_transfer_data_includes_async_results(self):
        async def fetch():
            return "data"

        result = AsyncResult(fetch)
        result._state.value = AsyncState.SUCCESS
        result._data.value = "collected"

        mock_component = self._make_component([result], component_id="test-cmp-1")
        mock_root = self._make_root([mock_component])

        payload = collect_transfer_data(mock_root)
        assert "test-cmp-1" in payload.async_results
        assert payload.async_results["test-cmp-1"].state == "success"
        assert payload.async_results["test-cmp-1"].data == "collected"

    def test_collect_skips_loading_async_results(self):
        async def fetch():
            return "data"

        loading = AsyncResult(fetch)
        loading._state.value = AsyncState.LOADING

        success_one = AsyncResult(fetch)
        success_one._state.value = AsyncState.SUCCESS
        success_one._data.value = "ok"

        mock_component = self._make_component([loading, success_one], component_id="cmp-loading")
        mock_root = self._make_root([mock_component])

        payload = collect_transfer_data(mock_root)
        assert "cmp-loading" in payload.async_results
        assert payload.async_results["cmp-loading"].state == "success"
        assert payload.async_results["cmp-loading"].data == "ok"

    def test_collect_transfer_data_includes_fetches_from_port(self):
        class _FakeFetchPort:
            @staticmethod
            def get_transfer_data():
                return {
                    "/api/data": TransferFetchEntry(status_code=200, headers={}, body="hello"),
                }

        scope = DIScope()
        scope.provide(FETCH_PORT_KEY, _FakeFetchPort())
        token = _active_di_scope.set(scope)
        try:

            async def fetch():
                return "data"

            result = AsyncResult(fetch)
            result._state.value = AsyncState.SUCCESS
            result._data.value = "x"

            mock_component = self._make_component([result], component_id="cmp")
            mock_root = self._make_root([mock_component])

            payload = collect_transfer_data(mock_root)
            assert "/api/data" in payload.fetches
            assert payload.fetches["/api/data"].body == "hello"
        finally:
            _active_di_scope.reset(token)
            scope.dispose()
