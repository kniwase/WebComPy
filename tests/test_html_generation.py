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


def _extract_py_config(html: str) -> dict:
    match = re.search(r'config="([^"]+)"', html)
    assert match is not None
    return json.loads(
        html.unescape(match.group(1)) if hasattr(html, "unescape") else match.group(1).replace("&quot;", '"')
    )


class TestGenerateHtmlDefaultMode:
    def test_packages_include_cdn_names(self):
        app = _make_app()
        html = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            pyodide_package_names=["numpy", "matplotlib"],
        )
        match = re.search(r'config="([^"]+)"', html)
        assert match is not None
        config_str = match.group(1).replace("&quot;", '"')
        config = json.loads(config_str)
        assert "numpy" in config["packages"]
        assert "matplotlib" in config["packages"]

    def test_no_lockfile_url_by_default(self):
        app = _make_app()
        html = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        match = re.search(r'config="([^"]+)"', html)
        assert match is not None
        config_str = match.group(1).replace("&quot;", '"')
        config = json.loads(config_str)
        assert "lockFileURL" not in config


class TestGenerateHtmlWasmLocalServing:
    def test_wasm_replaced_with_local_urls(self):
        app = _make_app()
        wasm_local_urls = {
            "numpy": "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
            "matplotlib": "/_webcompy-assets/packages/matplotlib-3.8.4-cp313-cp313-pyodide_2025_0_wasm32.whl",
        }
        html = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            pyodide_package_names=["numpy", "matplotlib"],
            wasm_local_urls=wasm_local_urls,
        )
        match = re.search(r'config="([^"]+)"', html)
        assert match is not None
        config_str = match.group(1).replace("&quot;", '"')
        config = json.loads(config_str)
        assert "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl" in config["packages"]
        assert "/_webcompy-assets/packages/matplotlib-3.8.4-cp313-cp313-pyodide_2025_0_wasm32.whl" in config["packages"]
        assert "numpy" not in config["packages"]
        assert "matplotlib" not in config["packages"]

    def test_cdn_packages_not_replaced(self):
        app = _make_app()
        wasm_local_urls = {
            "numpy": "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
        }
        html = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            pyodide_package_names=["numpy", "httpx"],
            wasm_local_urls=wasm_local_urls,
        )
        match = re.search(r'config="([^"]+)"', html)
        assert match is not None
        config_str = match.group(1).replace("&quot;", '"')
        config = json.loads(config_str)
        assert "httpx" in config["packages"]
        assert "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl" in config["packages"]

    def test_lockfile_url_cdn(self):
        app = _make_app()
        html = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            lockfile_url="https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json",
        )
        match = re.search(r'config="([^"]+)"', html)
        assert match is not None
        config_str = match.group(1).replace("&quot;", '"')
        config = json.loads(config_str)
        assert config["lockFileURL"] == "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json"

    def test_lockfile_url_local(self):
        app = _make_app()
        html = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            lockfile_url="/_webcompy-assets/pyodide/pyodide-lock.json",
        )
        match = re.search(r'config="([^"]+)"', html)
        assert match is not None
        config_str = match.group(1).replace("&quot;", '"')
        config = json.loads(config_str)
        assert config["lockFileURL"] == "/_webcompy-assets/pyodide/pyodide-lock.json"

    def test_combined_wasm_local_and_lockfile_url(self):
        app = _make_app()
        wasm_local_urls = {
            "numpy": "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
        }
        html = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            pyodide_package_names=["numpy"],
            wasm_local_urls=wasm_local_urls,
            lockfile_url="https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json",
        )
        match = re.search(r'config="([^"]+)"', html)
        assert match is not None
        config_str = match.group(1).replace("&quot;", '"')
        config = json.loads(config_str)
        assert "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl" in config["packages"]
        assert config["lockFileURL"] == "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json"
