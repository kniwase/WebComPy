from __future__ import annotations

import base64
import html as html_module
import inspect
import json
import zlib
from unittest.mock import MagicMock, patch

from webcompy.aio._async_result import AsyncResult, AsyncState
from webcompy.components._component import Component
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.hydration import _payload as payload_module
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

_NO_APP = object()


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
        assert result.__webcompy_transfer_version__ == 3
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
        assert result.__webcompy_transfer_version__ == 3

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
        unescaped = html_module.unescape(serialized)
        parsed = json.loads(unescaped)
        assert parsed["__webcompy_transfer_version__"] == 3
        assert "/test" in parsed["fetches"]
        assert parsed["resources"] == {}


class TestPayloadCompression:
    def _large_payload(self) -> TransferPayload:
        return TransferPayload(
            fetches={
                f"/api/items/{i}": TransferFetchEntry(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    body=json.dumps({"id": i, "name": "item-name-" + "x" * 200}),
                )
                for i in range(50)
            },
            async_results={
                f"cmp-{i}": TransferAsyncResultEntry(
                    state="success",
                    data={"result": list(range(50)), "label": "data-" + "y" * 100},
                )
                for i in range(10)
            },
        )

    def test_round_trip_preserves_all_fields(self):
        payload = self._large_payload()
        original_serialized = serialize_payload(payload, compression_threshold=0)
        compressed_serialized = serialize_payload(payload, compression_threshold=1024)
        result = deserialize_payload(compressed_serialized)
        assert result is not None
        assert result.__webcompy_transfer_version__ == 3
        assert set(result.fetches.keys()) == set(payload.fetches.keys())
        assert set(result.async_results.keys()) == set(payload.async_results.keys())
        first_url = next(iter(payload.fetches.keys()))
        assert result.fetches[first_url].body == payload.fetches[first_url].body
        first_cid = next(iter(payload.async_results.keys()))
        assert result.async_results[first_cid].data == payload.async_results[first_cid].data
        unescaped = html_module.unescape(compressed_serialized)
        envelope = json.loads(unescaped)
        assert envelope["__webcompy_compressed__"] is True
        expected_inner = json.loads(html_module.unescape(original_serialized))
        decoded = json.loads(zlib.decompress(base64.b64decode(envelope["data"])).decode("utf-8"))
        assert decoded == expected_inner

    def test_payload_below_threshold_is_not_compressed(self):
        payload = TransferPayload(
            fetches={"/api/data": TransferFetchEntry(status_code=200, headers={}, body="ok")},
        )
        serialized = serialize_payload(payload, compression_threshold=1024)
        unescaped = html_module.unescape(serialized)
        parsed = json.loads(unescaped)
        assert "__webcompy_compressed__" not in parsed
        assert parsed["__webcompy_transfer_version__"] == 3
        assert "/api/data" in parsed["fetches"]

    def test_threshold_none_disables_compression(self):
        payload = self._large_payload()
        serialized = serialize_payload(payload, compression_threshold=None)
        unescaped = html_module.unescape(serialized)
        parsed = json.loads(unescaped)
        assert "__webcompy_compressed__" not in parsed
        assert parsed["__webcompy_transfer_version__"] == 3

    def test_threshold_zero_disables_compression(self):
        payload = self._large_payload()
        serialized = serialize_payload(payload, compression_threshold=0)
        unescaped = html_module.unescape(serialized)
        parsed = json.loads(unescaped)
        assert "__webcompy_compressed__" not in parsed
        assert parsed["__webcompy_transfer_version__"] == 3

    def test_backward_compatible_with_uncompressed_payload(self):
        payload = TransferPayload(
            fetches={"/x": TransferFetchEntry(status_code=200, headers={}, body="ok")},
            async_results={"cmp": TransferAsyncResultEntry(state="success", data={"v": 1})},
        )
        uncompressed = serialize_payload(payload, compression_threshold=0)
        result = deserialize_payload(uncompressed)
        assert result is not None
        assert "/x" in result.fetches
        assert "cmp" in result.async_results
        assert result.async_results["cmp"].data == {"v": 1}

    def test_compressed_payload_is_smaller_for_signal_heavy_data(self):
        payload = self._large_payload()
        uncompressed = serialize_payload(payload, compression_threshold=0)
        compressed = serialize_payload(payload, compression_threshold=1024)
        assert len(compressed) < len(uncompressed)

    def test_envelope_contains_transfer_version_at_top_level(self):
        payload = self._large_payload()
        serialized = serialize_payload(payload, compression_threshold=1024)
        unescaped = html_module.unescape(serialized)
        envelope = json.loads(unescaped)
        assert envelope["__webcompy_compressed__"] is True
        assert envelope["__webcompy_transfer_version__"] == 3
        assert isinstance(envelope["data"], str)
        inner = json.loads(zlib.decompress(base64.b64decode(envelope["data"])).decode("utf-8"))
        assert inner["__webcompy_transfer_version__"] == 3

    def test_uses_only_stdlib_for_compression(self):
        src = inspect.getsource(payload_module)
        assert "import zlib" in src
        assert "import base64" in src
        assert "brotli" not in src.lower()

    def test_corrupted_compressed_payload_returns_none(self):
        envelope = {
            "__webcompy_compressed__": True,
            "__webcompy_transfer_version__": 2,
            "data": base64.b64encode(b"not-zlib-data").decode("ascii"),
        }
        text = html_module.escape(json.dumps(envelope, ensure_ascii=False), quote=True)
        assert deserialize_payload(text) is None

    def test_default_threshold_compresses_large_payload(self):
        payload = self._large_payload()
        serialized = serialize_payload(payload)
        unescaped = html_module.unescape(serialized)
        parsed = json.loads(unescaped)
        assert parsed["__webcompy_compressed__"] is True

    def test_inner_version_authoritative_on_mismatch(self):
        payload = self._large_payload()
        original_json = json.dumps(
            {
                "__webcompy_transfer_version__": payload.__webcompy_transfer_version__,
                "fetches": {},
                "async_results": {},
                "signals": {},
            },
            ensure_ascii=False,
        )
        compressed = zlib.compress(original_json.encode("utf-8"))
        envelope = {
            "__webcompy_compressed__": True,
            "__webcompy_transfer_version__": 999,
            "data": base64.b64encode(compressed).decode("ascii"),
        }
        text = html_module.escape(json.dumps(envelope, ensure_ascii=False), quote=True)
        result = deserialize_payload(text)
        assert result is not None
        assert result.__webcompy_transfer_version__ == payload.__webcompy_transfer_version__


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

    def test_collect_transfer_data_records_resources_via_port(self):
        """``collect_transfer_data`` reads recorded resources from the
        configured ``ResourcePort`` (when present in DI scope) and
        base64-encodes them into the payload's ``resources`` field.
        """
        from webcompy.ports._keys import RESOURCE_PORT_KEY

        class _FakeResourcePort:
            def get_recorded_resources(self):
                return {
                    "templates/card.html": b"<p>hello</p>",
                    "icons/star.png": b"\x89PNG_FAKE",
                }

        scope = DIScope()
        scope.provide(RESOURCE_PORT_KEY, _FakeResourcePort())
        token = _active_di_scope.set(scope)
        try:

            async def fetch():
                return "x"

            result = AsyncResult(fetch)
            result._state.value = AsyncState.SUCCESS
            result._data.value = "ok"

            mock_component = self._make_component([result], component_id="cmp")
            mock_root = self._make_root([mock_component])

            payload = collect_transfer_data(mock_root)

            assert "templates/card.html" in payload.resources
            assert base64.b64decode(payload.resources["templates/card.html"]) == b"<p>hello</p>"
            assert base64.b64decode(payload.resources["icons/star.png"]) == b"\x89PNG_FAKE"
        finally:
            _active_di_scope.reset(token)
            scope.dispose()

    def test_collect_transfer_data_empty_when_no_resource_port(self):
        async def fetch():
            return "x"

        result = AsyncResult(fetch)
        result._state.value = AsyncState.SUCCESS
        result._data.value = "ok"

        mock_component = self._make_component([result], component_id="cmp")
        mock_root = self._make_root([mock_component])

        payload = collect_transfer_data(mock_root)
        assert payload.resources == {}


class TestCollectTransferDataCompressionThreshold:
    def _make_root(self, compression_threshold):
        from webcompy.app._root_component import AppDocumentRoot

        root = AppDocumentRoot.__new__(AppDocumentRoot)
        root._async_results = []
        root._children = []
        root._property = {"component_id": ""}
        if compression_threshold is _NO_APP:
            root._app = None
        else:
            root._app = MagicMock()
            root._app.config.compression_threshold = compression_threshold
        return root

    def test_collect_transfer_data_reads_none_threshold_from_app_config(self):
        root = self._make_root(None)
        with patch("webcompy.app._root_component.serialize_payload") as serialize_mock:
            root._collect_transfer_data()
            serialize_mock.assert_called_once()
            assert serialize_mock.call_args.kwargs["compression_threshold"] is None

    def test_collect_transfer_data_reads_zero_threshold_from_app_config(self):
        root = self._make_root(0)
        with patch("webcompy.app._root_component.serialize_payload") as serialize_mock:
            root._collect_transfer_data()
            serialize_mock.assert_called_once()
            assert serialize_mock.call_args.kwargs["compression_threshold"] == 0

    def test_collect_transfer_data_reads_custom_threshold_from_app_config(self):
        root = self._make_root(4096)
        with patch("webcompy.app._root_component.serialize_payload") as serialize_mock:
            root._collect_transfer_data()
            serialize_mock.assert_called_once()
            assert serialize_mock.call_args.kwargs["compression_threshold"] == 4096

    def test_collect_transfer_data_uses_default_when_no_app(self):
        root = self._make_root(_NO_APP)
        with patch("webcompy.app._root_component.serialize_payload") as serialize_mock:
            root._collect_transfer_data()
            serialize_mock.assert_called_once()
            assert serialize_mock.call_args.kwargs["compression_threshold"] == 1024


class TestTransferPayloadResources:
    """v3 introduces a ``resources`` field carrying base64-encoded bytes
    keyed by package-relative path.
    """

    def test_v3_roundtrip_preserves_resources(self):
        encoded_html = base64.b64encode(b"<p>hello</p>").decode("ascii")
        encoded_png = base64.b64encode(b"\x89PNG_FAKE").decode("ascii")
        payload = TransferPayload(
            resources={
                "templates/card.html": encoded_html,
                "icons/star.png": encoded_png,
            },
        )
        serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert result.__webcompy_transfer_version__ == 3
        assert result.resources == {
            "templates/card.html": encoded_html,
            "icons/star.png": encoded_png,
        }

    def test_v2_payload_deserializes_with_empty_resources(self):
        serialized = json.dumps(
            {
                "__webcompy_transfer_version__": 2,
                "fetches": {},
                "async_results": {},
                "signals": {},
            }
        )
        text = html_module.escape(serialized, quote=True)
        result = deserialize_payload(text)
        assert result is not None
        assert result.__webcompy_transfer_version__ == 2
        assert result.resources == {}

    def test_v1_payload_deserializes_with_empty_resources(self):
        serialized = json.dumps(
            {
                "__webcompy_transfer_version__": 1,
                "fetches": {},
            }
        )
        text = html_module.escape(serialized, quote=True)
        result = deserialize_payload(text)
        assert result is not None
        assert result.resources == {}

    def test_unknown_version_rejected(self):
        serialized = json.dumps(
            {
                "__webcompy_transfer_version__": 999,
                "fetches": {},
                "resources": {"a.html": "abc"},
            }
        )
        text = html_module.escape(serialized, quote=True)
        result = deserialize_payload(text)
        assert result is None

    def test_v3_default_resources_is_empty(self):
        payload = TransferPayload()
        assert payload.resources == {}
        assert payload.__webcompy_transfer_version__ == 3
