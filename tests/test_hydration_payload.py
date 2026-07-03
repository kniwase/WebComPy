from __future__ import annotations

import json

from webcompy.hydration._payload import (
    TransferAsyncResultEntry,
    TransferFetchEntry,
    TransferPayload,
    deserialize_payload,
    serialize_payload,
)


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
        assert result.__webcompy_transfer_version__ == 1
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
        assert result.__webcompy_transfer_version__ == 1

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
        assert parsed["__webcompy_transfer_version__"] == 1
        assert "/test" in parsed["fetches"]
