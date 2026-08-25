import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from webcompy.ajax import HttpClient
from webcompy.di._scope import DIScope
from webcompy.ports import FETCH_PORT_KEY
from webcompy_server.ports._fetch import ServerFetchPort


class TestSsrFormDataIntegration:
    @pytest.mark.asyncio
    async def test_form_data_reaches_self_site_as_multipart_during_ssr(self):
        received: dict = {}

        async def submit(request: Request):
            received["content_type"] = request.headers.get("content-type", "")
            received["body"] = await request.body()
            return JSONResponse({"ok": True})

        port = ServerFetchPort()
        app = Starlette(routes=[Route("/api/submit", submit, methods=["POST"])])
        port.configure(app)
        scope = DIScope()
        scope.provide(FETCH_PORT_KEY, port)
        try:
            with scope:
                res = await HttpClient.post("/api/submit", form_data={"name": "value"})
            assert res.ok is True
            assert res.json() == {"ok": True}
            assert received["content_type"].startswith("multipart/form-data; boundary=")
            boundary = received["content_type"].rsplit("=", 1)[1]
            expected = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="name"\r\n\r\nvalue\r\n'.encode()
                + f"--{boundary}--\r\n".encode()
            )
            assert received["body"] == expected
        finally:
            await port.close()
