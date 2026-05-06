import pytest

pytestmark = pytest.mark.e2e


def test_eruda_not_loaded_without_debug_param(page_on, assert_no_console_errors):
    page = page_on("/")
    is_eruda_loaded = page.evaluate("typeof window.eruda !== 'undefined'")
    assert not is_eruda_loaded


def test_eruda_loaded_with_debug_param(page_on, assert_no_console_errors):
    page = page_on("/?debug=True")
    is_eruda_loaded = page.evaluate("typeof window.eruda !== 'undefined'")
    assert is_eruda_loaded
