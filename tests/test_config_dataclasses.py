from pathlib import Path

from webcompy.app._config import WebComPyAppConfig
from webcompy.cli.config._build_config import WebComPyBuildConfig
from webcompy.cli.config._server_config import LockfileSyncConfig, WebComPyServerConfig


class TestWebComPyAppConfig:
    def test_defaults(self):
        config = WebComPyAppConfig()
        assert config.base_url == "/"
        assert config.selector == "#webcompy-app"
        assert config.profile is False
        assert config.hydrate is True
        assert config.scripts == []
        assert config.plugins == []

    def test_base_url_normalization_trailing_slash(self):
        config = WebComPyAppConfig(base_url="app")
        assert config.base_url == "/app/"

    def test_base_url_normalization_leading_slash(self):
        config = WebComPyAppConfig(base_url="/app")
        assert config.base_url == "/app/"

    def test_base_url_normalization_both_slashes(self):
        config = WebComPyAppConfig(base_url="/app/")
        assert config.base_url == "/app/"

    def test_base_url_normalization_empty(self):
        config = WebComPyAppConfig(base_url="")
        assert config.base_url == "/"

    def test_base_url_normalization_root(self):
        config = WebComPyAppConfig(base_url="/")
        assert config.base_url == "/"

    def test_selector_default(self):
        config = WebComPyAppConfig()
        assert config.selector == "#webcompy-app"

    def test_custom_selector(self):
        config = WebComPyAppConfig(selector="#custom")
        assert config.selector == "#custom"

    def test_profile_default(self):
        config = WebComPyAppConfig()
        assert config.profile is False

    def test_profile_enabled(self):
        config = WebComPyAppConfig(profile=True)
        assert config.profile is True

    def test_hydrate_default(self):
        config = WebComPyAppConfig()
        assert config.hydrate is True

    def test_hydrate_false(self):
        config = WebComPyAppConfig(hydrate=False)
        assert config.hydrate is False


class TestWebComPyBuildConfig:
    def _make_module(self, tmp_path, code="app = None"):
        bootstrap = tmp_path / "bootstrap.py"
        bootstrap.write_text(code)
        import sys

        sys.path.insert(0, str(tmp_path))
        try:
            import importlib

            return importlib.import_module("bootstrap")
        finally:
            sys.path.pop(0)

    def _full_app_code(self):
        return (
            "from webcompy.app import WebComPyApp\n"
            "from webcompy.components._generator import define_component\n"
            "from webcompy.elements import html\n\n"
            "@define_component\n"
            "def Root(context):\n"
            "    return html.DIV({}, 'test')\n\n"
            "app = WebComPyApp(root_component=Root)\n"
        )

    def test_defaults(self, tmp_path):
        mod = self._make_module(tmp_path, self._full_app_code())
        config = WebComPyBuildConfig(app_module=mod)
        assert config.dependencies is None
        assert config.assets is None
        assert config.version is None
        assert config.wasm_serving == "cdn"
        assert config.runtime_serving == "cdn"
        assert config.wheel_mode == "bundled"
        assert config.standalone is False
        assert config.serve_all_deps is True
        assert config.dist == "dist"
        assert config.cname == ""
        assert config.static_files_dir == "static"
        assert isinstance(config.server, WebComPyServerConfig)
        assert isinstance(config.app_package_path, Path)

    def test_dependencies(self, tmp_path):
        mod = self._make_module(tmp_path, self._full_app_code())
        config = WebComPyBuildConfig(app_module=mod, dependencies=["numpy", "pandas"])
        assert config.dependencies == ["numpy", "pandas"]

    def test_assets(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, assets={"style.css": "/static/style.css"})
        assert config.assets == {"style.css": "/static/style.css"}

    def test_version_field(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, version="1.0.0")
        assert config.version == "1.0.0"

    def test_version_defaults_to_none(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod)
        assert config.version is None

    def test_wasm_serving_defaults_to_cdn(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod)
        assert config.wasm_serving == "cdn"

    def test_wasm_serving_explicit_cdn(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, wasm_serving="cdn")
        assert config.wasm_serving == "cdn"

    def test_wasm_serving_local(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, wasm_serving="local")
        assert config.wasm_serving == "local"

    def test_runtime_serving_defaults_to_cdn(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod)
        assert config.runtime_serving == "cdn"

    def test_runtime_serving_explicit_cdn(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, runtime_serving="cdn")
        assert config.runtime_serving == "cdn"

    def test_runtime_serving_local(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, runtime_serving="local")
        assert config.runtime_serving == "local"

    def test_wheel_mode_defaults_to_bundled(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod)
        assert config.wheel_mode == "bundled"

    def test_wheel_mode_split(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, wheel_mode="split")
        assert config.wheel_mode == "split"

    def test_wheel_mode_bundled_explicit(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, wheel_mode="bundled")
        assert config.wheel_mode == "bundled"


class TestWebComPyServerConfig:
    def test_defaults(self):
        config = WebComPyServerConfig()
        assert config.port == 8080
        assert config.dev is False

    def test_custom(self):
        config = WebComPyServerConfig(port=3000, dev=True)
        assert config.port == 3000
        assert config.dev is True


class TestLockfileSyncConfig:
    def test_defaults(self):
        config = LockfileSyncConfig()
        assert config.requirements_path is None
        assert config.sync_group is None

    def test_custom(self):
        config = LockfileSyncConfig(requirements_path="../requirements.txt", sync_group="browser")
        assert config.requirements_path == "../requirements.txt"
        assert config.sync_group == "browser"
