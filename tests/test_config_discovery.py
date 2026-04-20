import types
from unittest.mock import patch

import pytest

from webcompy.app._app import WebComPyApp
from webcompy.app._config import AppConfig
from webcompy.cli._exception import WebComPyCliException
from webcompy.cli._utils import (
    _extract_package,
    discover_app,
    get_generate_config,
    get_server_config,
)
from webcompy.components._generator import define_component


@define_component
def DiscoveryTestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "discovery test")


def _make_test_app():
    return WebComPyApp(root_component=DiscoveryTestRoot, config=AppConfig(app_package="test_app"))


class TestExtractPackage:
    def test_extracts_package_from_dotted_path(self):
        assert _extract_package("my_app.bootstrap:app") == "my_app"

    def test_extracts_nested_package(self):
        assert _extract_package("my_app.sub.bootstrap:app") == "my_app.sub"

    def test_returns_none_for_top_level_module(self):
        assert _extract_package("bootstrap:app") is None

    def test_raises_for_invalid_format(self):
        with pytest.raises(WebComPyCliException, match="Invalid app import path"):
            _extract_package("no_colon")


class TestGetServerConfig:
    def test_returns_default_when_no_module(self):
        config = get_server_config()
        assert config.port == 8080
        assert config.dev is False
        assert config.static_files_dir == "static"

    def test_returns_default_when_no_module_with_package(self):
        config = get_server_config(package="my_app")
        assert config.port == 8080

    def test_returns_config_from_package_module(self):
        from webcompy.app._config import ServerConfig

        mock_module = types.SimpleNamespace(server_config=ServerConfig(port=3000, dev=True))

        def mock_import(name):
            if name == "my_app.webcompy_server_config":
                return mock_module
            raise ModuleNotFoundError

        with patch("webcompy.cli._utils.import_module", side_effect=mock_import):
            config = get_server_config(package="my_app")
        assert config.port == 3000
        assert config.dev is True

    def test_returns_config_from_root_module(self):
        from webcompy.app._config import ServerConfig

        mock_module = types.SimpleNamespace(server_config=ServerConfig(port=3000, dev=True))

        def mock_import(name):
            if name == "webcompy_server_config":
                return mock_module
            raise ModuleNotFoundError

        with patch("webcompy.cli._utils.import_module", side_effect=mock_import):
            config = get_server_config()
        assert config.port == 3000
        assert config.dev is True

    def test_fallback_to_root_when_package_not_found(self):
        from webcompy.app._config import ServerConfig

        root_module = types.SimpleNamespace(server_config=ServerConfig(port=9000))

        def mock_import(name):
            if name == "webcompy_server_config":
                return root_module
            raise ModuleNotFoundError

        with patch("webcompy.cli._utils.import_module", side_effect=mock_import):
            config = get_server_config(package="my_app")
        assert config.port == 9000

    def test_returns_default_when_no_server_config_attr(self):
        mock_module = types.SimpleNamespace()

        def mock_import(name):
            if name == "webcompy_server_config":
                return mock_module
            raise ModuleNotFoundError

        with patch("webcompy.cli._utils.import_module", side_effect=mock_import):
            config = get_server_config()
        assert config.port == 8080

    def test_raises_when_wrong_type(self):
        mock_module = types.SimpleNamespace(server_config="not a config")

        def mock_import(name):
            if name == "webcompy_server_config":
                return mock_module
            raise ModuleNotFoundError

        with (
            patch("webcompy.cli._utils.import_module", side_effect=mock_import),
            pytest.raises(WebComPyCliException, match="not a ServerConfig"),
        ):
            get_server_config()


class TestGetGenerateConfig:
    def test_returns_default_when_no_module(self):
        config = get_generate_config()
        assert config.dist == "dist"
        assert config.cname == ""
        assert config.static_files_dir == "static"

    def test_returns_default_when_no_module_with_package(self):
        config = get_generate_config(package="my_app")
        assert config.dist == "dist"

    def test_returns_config_from_package_module(self):
        from webcompy.app._config import GenerateConfig

        mock_module = types.SimpleNamespace(generate_config=GenerateConfig(dist="out", cname="example.com"))

        def mock_import(name):
            if name == "my_app.webcompy_server_config":
                return mock_module
            raise ModuleNotFoundError

        with patch("webcompy.cli._utils.import_module", side_effect=mock_import):
            config = get_generate_config(package="my_app")
        assert config.dist == "out"
        assert config.cname == "example.com"

    def test_returns_config_from_root_module(self):
        from webcompy.app._config import GenerateConfig

        mock_module = types.SimpleNamespace(generate_config=GenerateConfig(dist="out", cname="example.com"))

        def mock_import(name):
            if name == "webcompy_server_config":
                return mock_module
            raise ModuleNotFoundError

        with patch("webcompy.cli._utils.import_module", side_effect=mock_import):
            config = get_generate_config()
        assert config.dist == "out"
        assert config.cname == "example.com"

    def test_fallback_to_root_when_package_not_found(self):
        from webcompy.app._config import GenerateConfig

        root_module = types.SimpleNamespace(generate_config=GenerateConfig(dist="build"))

        def mock_import(name):
            if name == "webcompy_server_config":
                return root_module
            raise ModuleNotFoundError

        with patch("webcompy.cli._utils.import_module", side_effect=mock_import):
            config = get_generate_config(package="my_app")
        assert config.dist == "build"

    def test_raises_when_wrong_type(self):
        mock_module = types.SimpleNamespace(generate_config="not a config")

        def mock_import(name):
            if name == "webcompy_server_config":
                return mock_module
            raise ModuleNotFoundError

        with (
            patch("webcompy.cli._utils.import_module", side_effect=mock_import),
            pytest.raises(WebComPyCliException, match="not a GenerateConfig"),
        ):
            get_generate_config()


class TestDiscoverApp:
    def test_uses_import_path_when_provided_returns_package(self):
        app = _make_test_app()
        with patch("webcompy.cli._utils.get_app_from_import_path", return_value=app) as mock:
            result, package = discover_app("my_app.bootstrap:app")
        mock.assert_called_once_with("my_app.bootstrap:app")
        assert result is app
        assert package == "my_app"

    def test_uses_import_path_top_level_returns_none_package(self):
        app = _make_test_app()
        with patch("webcompy.cli._utils.get_app_from_import_path", return_value=app) as mock:
            result, package = discover_app("bootstrap:app")
        mock.assert_called_once_with("bootstrap:app")
        assert result is app
        assert package is None

    def test_uses_webcompy_config_when_no_import_path(self):
        app = _make_test_app()
        mock_module = types.SimpleNamespace(app_import_path="my_app.bootstrap:app")
        with (
            patch("webcompy.cli._utils.import_module", return_value=mock_module),
            patch("webcompy.cli._utils.get_app_from_import_path", return_value=app) as mock,
        ):
            result, package = discover_app(None)
        mock.assert_called_once_with("my_app.bootstrap:app")
        assert result is app
        assert package == "my_app"

    def test_raises_when_no_module_and_no_import_path(self):
        with (
            patch("webcompy.cli._utils.import_module", side_effect=ModuleNotFoundError),
            pytest.raises(WebComPyCliException, match="webcompy_config"),
        ):
            discover_app(None)

    def test_raises_when_no_app_import_path_in_config(self):
        mock_module = types.SimpleNamespace()
        with (
            patch("webcompy.cli._utils.import_module", return_value=mock_module),
            pytest.raises(WebComPyCliException, match="app_import_path"),
        ):
            discover_app(None)
