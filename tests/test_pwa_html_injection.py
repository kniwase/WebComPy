from __future__ import annotations

from webcompy.components._generator import define_component
from webcompy_testing import create_test_app, render_app_html


@define_component()
def PwaRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "pwa")


def _render(base_url: str = "/", **kwargs) -> str:
    app = create_test_app(root_component=PwaRoot, base_url=base_url)
    return render_app_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=False,
        wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        **kwargs,
    )


class TestManifestLinkInjection:
    def test_absent_by_default(self):
        html_str = _render()
        assert 'rel="manifest"' not in html_str

    def test_present_when_enabled(self):
        html_str = _render(pwa_enabled=True)
        assert '<link rel="manifest" href="/manifest.webmanifest">' in html_str

    def test_href_uses_base_url(self):
        html_str = _render(base_url="/pwa/", pwa_enabled=True)
        assert '<link rel="manifest" href="/pwa/manifest.webmanifest">' in html_str

    def test_link_is_in_head(self):
        html_str = _render(pwa_enabled=True)
        head = html_str.split("</head>")[0]
        assert 'rel="manifest"' in head

    def test_pwa_enabled_defaults_false(self):
        html_str = _render(pwa_enabled=False)
        assert 'rel="manifest"' not in html_str
