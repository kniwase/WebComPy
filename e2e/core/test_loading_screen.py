import pytest

pytestmark = pytest.mark.e2e


def test_fade_class_present_before_removal(page, server_url):
    page.add_init_script(
        """
        new MutationObserver(function (mutations) {
            for (var m of mutations) {
                if (m.type === 'attributes' && m.attributeName === 'class') {
                    var el = m.target;
                    if (el.id === 'webcompy-loading' && el.classList.contains('wc-fading')) {
                        window.__wcFadingSeen = true;
                    }
                }
            }
        }).observe(document, {subtree: true, attributes: true});
        """
    )
    page.goto(server_url)
    page.wait_for_selector("#webcompy-loading", state="hidden")
    assert page.evaluate("window.__wcFadingSeen === true")
