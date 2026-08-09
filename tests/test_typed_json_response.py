from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from webcompy.exception import WebComPyException
from webcompy.hydration._transfer_meta import META_BODY_KEY, META_HEADER_NAME
from webcompy_server.contrib.fastapi import TypedJSONResponse


@dataclass
class Record:
    name: str
    blob: bytes
    tags: set[str]
    price: Decimal
    at: datetime


def _record() -> Record:
    return Record(
        name="alice",
        blob=b"img",
        tags={"a", "b"},
        price=Decimal("12.34"),
        at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    )


class TestHeaderMode:
    def test_default_mode_is_header(self):
        app = FastAPI()

        @app.get("/record")
        def record() -> TypedJSONResponse:
            return TypedJSONResponse(_record())

        response = TestClient(app).get("/record")
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "alice"
        assert body["blob"] == "aW1n"
        assert set(body["tags"]) == {"a", "b"}
        assert body["price"] == "12.34"
        assert META_BODY_KEY not in body
        assert not any(key.startswith("__webcompy_") for key in body)
        meta = json.loads(response.headers[META_HEADER_NAME])
        assert meta == {
            "/blob": "bytes",
            "/tags": "set",
            "/price": "decimal",
            "/at": "datetime",
        }

    def test_plain_client_consumes_body_normally(self):
        app = FastAPI()

        @app.get("/record")
        def record() -> TypedJSONResponse:
            return TypedJSONResponse(_record())

        response = TestClient(app).get("/record")
        assert response.json()["name"] == "alice"
        assert response.json()["price"] == "12.34"

    def test_top_level_array_in_header_mode(self):
        app = FastAPI()

        @app.get("/items")
        def items() -> TypedJSONResponse:
            return TypedJSONResponse([b"a", b"b"])

        response = TestClient(app).get("/items")
        assert response.json() == ["YQ==", "Yg=="]
        assert json.loads(response.headers[META_HEADER_NAME]) == {"/0": "bytes", "/1": "bytes"}

    def test_no_meta_no_header(self):
        app = FastAPI()

        @app.get("/plain")
        def plain() -> TypedJSONResponse:
            return TypedJSONResponse({"name": "alice"})

        response = TestClient(app).get("/plain")
        assert META_HEADER_NAME not in response.headers


class TestBodyMode:
    def test_body_mode_injects_meta_key(self):
        app = FastAPI()

        @app.get("/record")
        def record() -> TypedJSONResponse:
            return TypedJSONResponse(_record(), transfer_mode="body")

        response = TestClient(app).get("/record")
        body = response.json()
        assert body["name"] == "alice"
        assert body["tags"] == {"a", "b"} or set(body["tags"]) == {"a", "b"}
        assert body[META_BODY_KEY] == {
            "/blob": "bytes",
            "/tags": "set",
            "/price": "decimal",
            "/at": "datetime",
        }
        assert META_HEADER_NAME not in response.headers

    def test_array_payload_in_body_mode_raises(self):
        with pytest.raises(WebComPyException, match="top-level JSON object"):
            TypedJSONResponse([1, 2], transfer_mode="body")

    def test_scalar_payload_in_body_mode_raises(self):
        with pytest.raises(WebComPyException, match="top-level JSON object"):
            TypedJSONResponse(42, transfer_mode="body")


class TestImportSafety:
    def test_import_without_starlette_raises_clear_error(self, monkeypatch):
        module = importlib.import_module("webcompy_server.contrib.fastapi")
        monkeypatch.setitem(sys.modules, "starlette", None)
        monkeypatch.setitem(sys.modules, "starlette.responses", None)
        with pytest.raises(ImportError, match="fastapi"):
            importlib.reload(module)

    def test_server_package_imports_without_starlette(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "starlette", None)
        monkeypatch.setitem(sys.modules, "starlette.responses", None)
        import webcompy_server  # noqa: F401

    def test_contrib_package_imports_without_starlette(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "starlette", None)
        monkeypatch.setitem(sys.modules, "starlette.responses", None)
        import webcompy_server.contrib  # noqa: F401
