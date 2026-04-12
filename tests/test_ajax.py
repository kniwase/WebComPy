from webcompy.ajax._fetch import Response, WebComPyHttpClientException


class TestResponse:
    def test_basic_response(self):
        r = Response(text="hello", headers={"content-type": "text/plain"}, status_code=200, reason="OK", ok=True)
        assert r.text == "hello"
        assert r.headers == {"content-type": "text/plain"}
        assert r.status_code == 200
        assert r.ok is True

    def test_error_response(self):
        r = Response(text="not found", headers={}, status_code=404, reason="Not Found", ok=False)
        assert r.ok is False

    def test_json_parsing(self):
        r = Response(
            text='{"key": "value"}', headers={"content-type": "application/json"}, status_code=200, reason="OK", ok=True
        )
        assert r.json() == {"key": "value"}

    def test_raise_for_status_success(self):
        r = Response(text="ok", headers={}, status_code=200, reason="OK", ok=True)
        r.raise_for_status()

    def test_raise_for_status_error(self):
        r = Response(text="error", headers={}, status_code=500, reason="Internal Server Error", ok=False)
        try:
            r.raise_for_status()
            raise AssertionError("Should have raised")
        except WebComPyHttpClientException:
            pass

    def test_repr(self):
        r = Response(text="ok", headers={}, status_code=200, reason="OK", ok=True)
        r = repr(r)
        assert "200" in r
