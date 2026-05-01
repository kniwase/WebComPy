from pathlib import Path

from webcompy.app._config import AppConfig, GenerateConfig, ServerConfig


class TestAppConfig:
    def test_defaults(self):
        config = AppConfig()
        assert config.base_url == "/"
        assert config.dependencies is None
        assert config.assets is None
        assert config.version is None
        assert config.app_package_path is not None

    def test_base_url_normalization_trailing_slash(self):
        config = AppConfig(base_url="app")
        assert config.base_url == "/app/"

    def test_base_url_normalization_leading_slash(self):
        config = AppConfig(base_url="/app")
        assert config.base_url == "/app/"

    def test_base_url_normalization_both_slashes(self):
        config = AppConfig(base_url="/app/")
        assert config.base_url == "/app/"

    def test_base_url_normalization_empty(self):
        config = AppConfig(base_url="")
        assert config.base_url == "/"

    def test_base_url_normalization_root(self):
        config = AppConfig(base_url="/")
        assert config.base_url == "/"

    def test_dependencies(self):
        config = AppConfig(dependencies=["numpy", "pandas"])
        assert config.dependencies == ["numpy", "pandas"]

    def test_assets(self):
        config = AppConfig(assets={"style.css": "/static/style.css"})
        assert config.assets == {"style.css": "/static/style.css"}

    def test_app_package_path_from_string(self):
        config = AppConfig(app_package="myapp")
        assert config.app_package_path is not None
        assert str(config.app_package_path).endswith("myapp")

    def test_app_package_path_from_path(self):
        config = AppConfig(app_package=Path("/tmp/myapp"))
        assert config.app_package_path == Path("/tmp/myapp")

    def test_version_field(self):
        config = AppConfig(version="1.0.0")
        assert config.version == "1.0.0"

    def test_version_defaults_to_none(self):
        config = AppConfig()
        assert config.version is None

    def test_wasm_serving_defaults_to_none(self):
        config = AppConfig()
        assert config.wasm_serving is None

    def test_wasm_serving_cdn(self):
        config = AppConfig(wasm_serving="cdn")
        assert config.wasm_serving == "cdn"

    def test_wasm_serving_local(self):
        config = AppConfig(wasm_serving="local")
        assert config.wasm_serving == "local"


class TestServerConfig:
    def test_defaults(self):
        config = ServerConfig()
        assert config.port == 8080
        assert config.dev is False
        assert config.static_files_dir == "static"

    def test_custom(self):
        config = ServerConfig(port=3000, dev=True, static_files_dir="public")
        assert config.port == 3000
        assert config.dev is True
        assert config.static_files_dir == "public"


class TestGenerateConfig:
    def test_defaults(self):
        config = GenerateConfig()
        assert config.dist == "dist"
        assert config.cname == ""
        assert config.static_files_dir == "static"

    def test_custom(self):
        config = GenerateConfig(dist="out", cname="example.com", static_files_dir="public")
        assert config.dist == "out"
        assert config.cname == "example.com"
        assert config.static_files_dir == "public"
