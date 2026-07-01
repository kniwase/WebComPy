import json
import re

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.components._generator import define_component
from webcompy_server import configure_server_context
from webcompy_server._html import generate_html
from webcompy_testing._utils import run_sync


@define_component
def _TestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "test")


def _make_app(**config_kwargs):
    app = WebComPyApp(
        root_component=_TestRoot,
        config=WebComPyAppConfig(**config_kwargs),
    )
    configure_server_context(app)
    return app


def _generate_html(app, **kwargs):
    ctx = app.create_render_context()
    try:
        return run_sync(generate_html(ctx, **kwargs))
    finally:
        ctx.dispose()


def _extract_py_config(html_str: str) -> dict:
    match = re.search(r'config="([^"]+)"', html_str)
    assert match is not None
    return json.loads(match.group(1).replace("&quot;", '"'))


class TestRuntimeLocalHtmlIntegration:
    def test_runtime_local_with_wasm_local(self):
        app = _make_app()
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="local",
            pyodide_package_names=["numpy"],
            wasm_local_urls={"numpy": "/_webcompy-assets/packages/numpy.whl"},
            lockfile_url="https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json",
        )
        config = _extract_py_config(html_str)
        assert config["interpreter"] == "/_webcompy-assets/pyodide/pyodide.mjs"
        assert config["lockFileURL"] == "/_webcompy-assets/pyodide/pyodide-lock.json"
        assert "/_webcompy-assets/packages/numpy.whl" in config["packages"]

    def test_no_external_cdn_urls_in_runtime_local_html(self):
        app = _make_app()
        html_str = _generate_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="local",
        )
        assert "pyscript.net" not in html_str
        assert "cdn.jsdelivr.net/pyodide" not in html_str
