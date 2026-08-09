from __future__ import annotations

from datetime import UTC, datetime

import webcompy.ports._browser._cookie as _cookie_module
from webcompy.ports._browser._cookie import BrowserCookiePort

EXPIRES = datetime(2024, 1, 1, tzinfo=UTC)


def _make_port(fake_browser, monkeypatch):
    monkeypatch.setattr("webcompy.utils._environment.ENVIRONMENT", "pyscript")
    monkeypatch.setattr("webcompy.ports._browser._cookie.ENVIRONMENT", "pyscript")
    monkeypatch.setattr(_cookie_module, "_raw_browser", fake_browser)
    return BrowserCookiePort()


def test_set_with_expires_and_domain_applies_attributes(fake_browser, monkeypatch):
    port = _make_port(fake_browser, monkeypatch)

    port.set("session", "abc", expires=EXPIRES, domain="example.com")

    cookie = fake_browser.document.cookie
    assert cookie.startswith("session=abc")
    assert "; expires=Mon, 01 Jan 2024 00:00:00 GMT" in cookie
    assert "; domain=example.com" in cookie


def test_set_without_expires_and_domain_keeps_previous_output(fake_browser, monkeypatch):
    port = _make_port(fake_browser, monkeypatch)

    port.set("session", "abc", max_age=3600, secure=True, samesite="Strict")

    cookie = fake_browser.document.cookie
    assert cookie == "session=abc; max-age=3600; path=/; secure; samesite=Strict"
