import re

from webcompy.app._app import WebComPyApp
from webcompy.app._config import AppConfig
from webcompy.cli._html import generate_html
from webcompy.components._generator import define_component


@define_component
def _PrerenderTestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "test content")


def _make_app():
    return WebComPyApp(
        root_component=_PrerenderTestRoot,
        config=AppConfig(app_package="."),
    )


class TestPrerenderHiddenAttribute:
    def test_prerender_output_has_no_hidden(self):
        app = _make_app()
        html = generate_html(
            app,
            dev_mode=False,
            prerender=True,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        match = re.search(r'<div id="webcompy-app"[^>]*>', html)
        assert match is not None
        tag = match.group()
        assert "hidden" not in tag

    def test_non_prerender_output_has_hidden(self):
        app = _make_app()
        html = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        match = re.search(r'<div id="webcompy-app"[^>]*>', html)
        assert match is not None
        tag = match.group()
        assert "hidden" in tag
