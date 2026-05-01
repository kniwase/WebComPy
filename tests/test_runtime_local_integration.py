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


def _extract_script_src(html_str: str) -> str | None:
    match = re.search(r'<script[^>]+src="([^"]+)"', html_str)
    return match.group(1) if match else None


def _extract_css_href(html_str: str) -> str | None:
    match = re.search(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html_str)
    if match:
        return match.group(1)
    match = re.search(r'<link[^>]+href="([^"]+)"[^>]+rel="stylesheet"', html_str)
    return match.group(1) if match else None


class TestRuntimeLocalHtmlIntegration:
    def test_runtime_local_html_uses_local_assets(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="local",
        )
        script_src = _extract_script_src(html_str)
        css_href = _extract_css_href(html_str)
        assert script_src == "/_webcompy-assets/core.js"
        assert css_href == "/_webcompy-assets/core.css"

    def test_runtime_local_py_config(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="local",
        )
        config = _extract_py_config(html_str)
        assert config["interpreter"] == "/_webcompy-assets/pyodide/pyodide.mjs"
        assert config["lockFileURL"] == "/_webcompy-assets/pyodide/pyodide-lock.json"

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

    def test_runtime_cdn_wasm_local_lockfile(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="cdn",
            lockfile_url="https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json",
        )
        config = _extract_py_config(html_str)
        assert "interpreter" not in config
        assert config["lockFileURL"] == "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json"
        script_src = _extract_script_src(html_str)
        assert "pyscript.net" in script_src

    def test_runtime_local_with_base_url(self):
        app = _make_app(base_url="/myapp/")
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="local",
        )
        config = _extract_py_config(html_str)
        assert config["interpreter"] == "/myapp/_webcompy-assets/pyodide/pyodide.mjs"
        assert config["lockFileURL"] == "/myapp/_webcompy-assets/pyodide/pyodide-lock.json"
        script_src = _extract_script_src(html_str)
        assert script_src == "/myapp/_webcompy-assets/core.js"

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
