import pytest


@pytest.mark.skip(reason="Fetch Sample requires sample.json static file - see feat-docs-app-rename")
@pytest.mark.e2e
def test_fetch_page_loads(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/fetch")
    heading = page.get_by_role("heading", name="User Data")
    assert heading.is_visible()
