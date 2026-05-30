from __future__ import annotations

import pytest

from webcompy.aio._utils import run_sync
from webcompy.app._config import PluginScript, WebComPyAppConfig
from webcompy.cli._html import generate_html


def _make_app(**config_kwargs):
    from webcompy.app import WebComPyApp
    from webcompy.components._generator import define_component
    from webcompy.elements import html

    @define_component
    def _TestRoot(context):
        return html.DIV({}, "test")

    return WebComPyApp(
        root_component=_TestRoot,
        config=WebComPyAppConfig(**config_kwargs),
    )


def _generate_html(app, **kwargs):
    ctx = app.create_render_context()
    try:
        return run_sync(generate_html(ctx, **kwargs))
    finally:
        ctx.dispose()


class TestPluginScript:
    def test_defaults(self):
        ps = PluginScript(attrs={"type": "text/javascript"})
        assert ps.attrs == {"type": "text/javascript"}
        assert ps.script is None
        assert ps.condition is None
        assert ps.in_head is False

    def test_with_all_fields(self):
        ps = PluginScript(
            attrs={"src": "https://example.com/lib.js"},
            script="init();",
            condition="location.search.includes('debug')",
            in_head=True,
        )
        assert ps.script == "init();"
        assert ps.condition == "location.search.includes('debug')"
        assert ps.in_head is True

    def test_default_scripts_field(self):
        config = WebComPyAppConfig()
        assert config.scripts == []

    def test_scripts_with_plugin_scripts(self):
        ps = PluginScript(attrs={"src": "https://example.com/lib.js"})
        config = WebComPyAppConfig(scripts=[ps])
        assert len(config.scripts) == 1
        assert config.scripts[0] is ps


class TestGenerateHtmlWithPluginScripts:
    def test_unconditional_plugin_script_renders_as_static_tag(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={"type": "text/javascript", "src": "https://example.com/lib.js"},
                    in_head=True,
                )
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert '<script type="text/javascript" src="https://example.com/lib.js"></script>' in html_str
        assert "URLSearchParams" not in html_str

    def test_unconditional_inline_plugin_script(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={"type": "text/javascript"},
                    script="console.log('hello')",
                )
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "console.log('hello')" in html_str

    def test_conditional_plugin_script_generates_wrapper(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={"type": "text/javascript", "src": "https://example.com/eruda.min.js"},
                    condition="new URLSearchParams(location.search).get('debug') === 'True'",
                    in_head=True,
                )
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "URLSearchParams(location.search).get('debug')" in html_str
        assert "https://example.com/eruda.min.js" in html_str
        assert "(function(){" in html_str

    def test_conditional_plugin_script_with_inline_code(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={"type": "text/javascript", "src": "https://example.com/debug.js"},
                    condition="location.hash === '#debug'",
                    script="initDebug()",
                )
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "initDebug()" in html_str
        assert "onload" in html_str

    def test_conditional_plugin_script_inline_only_no_src(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={},
                    condition="location.search.includes('debug')",
                    script="console.log('debug mode')",
                )
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "console.log('debug mode')" in html_str
        assert "createElement" not in html_str
        assert "onload" not in html_str

    @pytest.mark.asyncio
    async def test_existing_append_script_still_works(self):
        app = _make_app()
        ctx = app.create_render_context()
        ctx.append_script({"type": "text/javascript", "src": "https://example.com/analytics.js"})
        html_str = await generate_html(
            ctx,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        ctx.dispose()
        assert "https://example.com/analytics.js" in html_str

    def test_conditional_head_script_placed_in_head(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={"src": "https://example.com/lib.js"},
                    condition="true",
                    in_head=True,
                )
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        head_section = html_str.split("<body>")[0]
        assert "document.head.appendChild" in head_section

    def test_conditional_body_script_placed_in_body(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={"src": "https://example.com/lib.js"},
                    condition="true",
                    in_head=False,
                )
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        body_section = html_str.split("<body>")[1]
        assert "document.body.appendChild" in body_section

    def test_multiple_conditional_scripts(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={"src": "https://example.com/script1.js"},
                    condition="cond1",
                ),
                PluginScript(
                    attrs={"src": "https://example.com/script2.js"},
                    condition="cond2",
                ),
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert html_str.count("(function(){") == 2
        assert "cond1" in html_str
        assert "cond2" in html_str

    def test_unconditional_head_script_placement(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={"type": "text/javascript", "src": "https://example.com/head.js"},
                    in_head=True,
                )
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        head_section = html_str.split("<body>")[0]
        assert "https://example.com/head.js" in head_section

    def test_unconditional_body_script_placement(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={"type": "text/javascript", "src": "https://example.com/body.js"},
                    in_head=False,
                )
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        body_section = html_str.split("<body>")[1]
        assert "https://example.com/body.js" in body_section

    def test_inline_only_script_with_condition_and_none_script(self):
        app = _make_app(
            scripts=[
                PluginScript(
                    attrs={},
                    condition="true",
                )
            ]
        )
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "onload" not in html_str
        assert "createElement" not in html_str
