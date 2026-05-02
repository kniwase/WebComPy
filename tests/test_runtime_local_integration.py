from __future__ import annotations

import json
import re

from webcompy.app._app import WebComPyApp
from webcompy.app._config import AppConfig
from webcompy.cli._html import generate_html
from webcompy.components._generator import define_component


@define_component
def _TestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "test")


def _make_app(**config_kwargs):
    return WebComPyApp(
        root_component=_TestRoot,
        config=AppConfig(app_package=".", **config_kwargs),
    )


def _extract_py_config(html_str: str) -> dict:
    match = re.search(r'config="([^"]+)"', html_str)
    assert match is not None
    return json.loads(match.group(1).replace("&quot;", '"'))


class TestRuntimeLocalHtmlIntegration:
    def test_runtime_local_with_wasm_local(self):
        app = _make_app()
        html_str = generate_html(
            app,
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
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="local",
        )
        assert "pyscript.net" not in html_str
        assert "cdn.jsdelivr.net/pyodide" not in html_str
