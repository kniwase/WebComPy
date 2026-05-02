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


class TestGenerateHtmlDefaultMode:
    def test_packages_include_cdn_names(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            pyodide_package_names=["numpy", "matplotlib"],
        )
        config = _extract_py_config(html_str)
        assert "numpy" in config["packages"]
        assert "matplotlib" in config["packages"]

    def test_no_lockfile_url_by_default(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        config = _extract_py_config(html_str)
        assert "lockFileURL" not in config


class TestGenerateHtmlWasmLocalServing:
    def test_wasm_replaced_with_local_urls(self):
        app = _make_app()
        wasm_local_urls = {
            "numpy": "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
            "matplotlib": "/_webcompy-assets/packages/matplotlib-3.8.4-cp313-cp313-pyodide_2025_0_wasm32.whl",
        }
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            pyodide_package_names=["numpy", "matplotlib"],
            wasm_local_urls=wasm_local_urls,
        )
        config = _extract_py_config(html_str)
        assert "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl" in config["packages"]
        assert "/_webcompy-assets/packages/matplotlib-3.8.4-cp313-cp313-pyodide_2025_0_wasm32.whl" in config["packages"]
        assert "numpy" not in config["packages"]
        assert "matplotlib" not in config["packages"]

    def test_cdn_packages_not_replaced(self):
        app = _make_app()
        wasm_local_urls = {
            "numpy": "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
        }
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            pyodide_package_names=["numpy", "httpx"],
            wasm_local_urls=wasm_local_urls,
        )
        config = _extract_py_config(html_str)
        assert "httpx" in config["packages"]
        assert "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl" in config["packages"]

    def test_lockfile_url_cdn(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            lockfile_url="https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json",
        )
        config = _extract_py_config(html_str)
        assert config["lockFileURL"] == "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json"

    def test_lockfile_url_local(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            lockfile_url="/_webcompy-assets/pyodide/pyodide-lock.json",
        )
        config = _extract_py_config(html_str)
        assert config["lockFileURL"] == "/_webcompy-assets/pyodide/pyodide-lock.json"

    def test_combined_wasm_local_and_lockfile_url(self):
        app = _make_app()
        wasm_local_urls = {
            "numpy": "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
        }
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            pyodide_package_names=["numpy"],
            wasm_local_urls=wasm_local_urls,
            lockfile_url="https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json",
        )
        config = _extract_py_config(html_str)
        assert "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl" in config["packages"]
        assert config["lockFileURL"] == "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json"


def _extract_script_src(html_str: str) -> str | None:
    match = re.search(r'<script[^>]+src="([^"]+)"', html_str)
    return match.group(1) if match else None


def _extract_css_href(html_str: str) -> str | None:
    match = re.search(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html_str)
    if match:
        return match.group(1)
    match = re.search(r'<link[^>]+href="([^"]+)"[^>]+rel="stylesheet"', html_str)
    return match.group(1) if match else None


class TestGenerateHtmlRuntimeLocalServing:
    def test_runtime_local_script_src(self):
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
        assert script_src == "/_webcompy-assets/core.js"

    def test_runtime_local_css_href(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="local",
        )
        css_href = _extract_css_href(html_str)
        assert css_href == "/_webcompy-assets/core.css"

    def test_runtime_local_py_config_includes_interpreter_and_lockfile(self):
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

    def test_runtime_cdn_no_interpreter_no_lockfile(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="cdn",
        )
        config = _extract_py_config(html_str)
        assert "interpreter" not in config
        assert "lockFileURL" not in config

    def test_runtime_cdn_script_and_css_use_cdn(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="cdn",
        )
        script_src = _extract_script_src(html_str)
        css_href = _extract_css_href(html_str)
        assert "pyscript.net" in script_src
        assert "pyscript.net" in css_href

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
        css_href = _extract_css_href(html_str)
        assert script_src == "/myapp/_webcompy-assets/core.js"
        assert css_href == "/myapp/_webcompy-assets/core.css"

    def test_runtime_local_overrides_lockfile_url(self):
        app = _make_app()
        html_str = generate_html(
            app,
            dev_mode=False,
            prerender=False,
            app_version="0.0.0",
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            runtime_serving="local",
            lockfile_url="https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json",
        )
        config = _extract_py_config(html_str)
        assert config["lockFileURL"] == "/_webcompy-assets/pyodide/pyodide-lock.json"
        assert config["interpreter"] == "/_webcompy-assets/pyodide/pyodide.mjs"

    def test_runtime_cdn_wasm_local_lockfile_url(self):
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
