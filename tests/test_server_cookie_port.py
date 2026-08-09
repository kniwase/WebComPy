from __future__ import annotations

from datetime import UTC, datetime

from webcompy_server.ports._cookie import ServerCookiePort

EXPIRES = datetime(2024, 1, 1, tzinfo=UTC)


class TestServerCookiePortSet:
    def test_full_attribute_set_produces_set_cookie_header(self) -> None:
        port = ServerCookiePort()
        port.set(
            "session",
            "abc",
            max_age=3600,
            expires=EXPIRES,
            path="/",
            domain="example.com",
            secure=True,
            httponly=True,
            samesite="Strict",
        )

        headers = port.get_pending_set_cookie_headers()

        assert len(headers) == 1
        header = headers[0]
        assert header.startswith("session=abc")
        assert "Max-Age=3600" in header
        assert "expires=Mon, 01 Jan 2024 00:00:00 GMT" in header
        assert "Domain=example.com" in header
        assert "Path=/" in header
        assert "Secure" in header
        assert "HttpOnly" in header
        assert "SameSite=Strict" in header

    def test_default_attributes_produce_minimal_header(self) -> None:
        port = ServerCookiePort()
        port.set("session", "abc")

        header = port.get_pending_set_cookie_headers()[0]

        assert header == "session=abc; Path=/"
        assert "Secure" not in header
        assert "HttpOnly" not in header
        assert "SameSite" not in header

    def test_naive_expires_is_treated_as_utc(self) -> None:
        port = ServerCookiePort()
        port.set("session", "abc", expires=datetime(2024, 1, 1))

        header = port.get_pending_set_cookie_headers()[0]

        assert "expires=Mon, 01 Jan 2024 00:00:00 GMT" in header

    def test_read_path_updated_by_set(self) -> None:
        port = ServerCookiePort()
        port.set("session", "abc")

        assert port.get("session") == "abc"
        assert port.get_all() == {"session": "abc"}

    def test_values_requiring_quoting_are_serialized(self) -> None:
        port = ServerCookiePort()
        port.set("session", "a;b c")

        header = port.get_pending_set_cookie_headers()[0]

        assert "a\\073b c" in header or '"a;b c"' in header


class TestServerCookiePortMultipleWrites:
    def test_multiple_cookies_produce_one_header_each(self) -> None:
        port = ServerCookiePort()
        port.set("session", "abc")
        port.set("theme", "dark")

        headers = port.get_pending_set_cookie_headers()

        assert len(headers) == 2
        assert headers[0].startswith("session=abc")
        assert headers[1].startswith("theme=dark")

    def test_last_write_wins_for_same_name_and_path(self) -> None:
        port = ServerCookiePort()
        port.set("session", "abc")
        port.set("session", "def")

        headers = port.get_pending_set_cookie_headers()

        assert len(headers) == 1
        assert headers[0].startswith("session=def")

    def test_same_name_different_path_produces_two_headers(self) -> None:
        port = ServerCookiePort()
        port.set("session", "abc", path="/")
        port.set("session", "def", path="/admin")

        headers = port.get_pending_set_cookie_headers()

        assert len(headers) == 2

    def test_pending_writes_do_not_leak_between_instances(self) -> None:
        port1 = ServerCookiePort()
        port2 = ServerCookiePort()
        port1.set("session", "abc")

        assert port2.get_pending_set_cookie_headers() == []


class TestServerCookiePortDelete:
    def test_delete_emits_expiring_set_cookie(self) -> None:
        port = ServerCookiePort()
        port.set("session", "abc", path="/")
        port.delete("session", path="/")

        headers = port.get_pending_set_cookie_headers()

        assert len(headers) == 1
        header = headers[0]
        assert header.startswith("session=")
        assert "Max-Age=0" in header

    def test_delete_removes_cookie_from_read_path(self) -> None:
        port = ServerCookiePort()
        port.set("session", "abc")
        port.delete("session")

        assert port.get("session") is None
        assert port.get_all() == {}
