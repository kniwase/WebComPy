import re

import pytest

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.cli._html import generate_html
from webcompy.components._generator import define_component


@define_component
def _PrerenderTestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "test content")


def _make_app():
    return WebComPyApp(
        root_component=_PrerenderTestRoot,
        config=WebComPyAppConfig(),
    )


class TestPrerenderHiddenAttribute:
    @pytest.mark.asyncio
    async def test_prerender_output_has_no_hidden(self):
        app = _make_app()
        ctx = app.create_render_context()
        html = await generate_html(
            ctx,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        ctx.dispose()
        match = re.search(r'<div id="webcompy-app"[^>]*>', html)
        assert match is not None
        tag = match.group()
        assert "hidden" not in tag

    @pytest.mark.asyncio
    async def test_non_prerender_output_has_hidden(self):
        app = _make_app()
        ctx = app.create_render_context()
        html = await generate_html(
            ctx,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        ctx.dispose()
        match = re.search(r'<div id="webcompy-app"[^>]*>', html)
        assert match is not None
        tag = match.group()
        assert "hidden" in tag
