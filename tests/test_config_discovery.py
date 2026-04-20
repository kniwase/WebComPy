import types
from unittest.mock import patch

import pytest

from webcompy.app._app import WebComPyApp
from webcompy.app._config import AppConfig
from webcompy.cli._exception import WebComPyCliException
from webcompy.cli._utils import discover_app, get_generate_config, get_server_config
from webcompy.components._generator import define_component


@define_component
def DiscoveryTestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "discovery test")


def _make_test_app():
    return WebComPyApp(root_component=DiscoveryTestRoot, config=AppConfig(app_package="test_app"))


class TestGetServerConfig:
    def test_returns_default_when_no_module(self):
        config = get_server_config()
        assert config.port == 8080
        assert config.dev is False
        assert config.static_files_dir == "static"

    def test_returns_config_from_module(self):
        from webcompy.app._config import ServerConfig

        mock_module = types.SimpleNamespace(server_config=ServerConfig(port=3000, dev=True))
        with patch("webcompy.cli._utils.import_module", return_value=mock_module):
            config = get_server_config()
        assert config.port == 3000
        assert config.dev is True

    def test_returns_default_when_no_server_config_attr(self):
        mock_module = types.SimpleNamespace()
        with patch("webcompy.cli._utils.import_module", return_value=mock_module):
            config = get_server_config()
        assert config.port == 8080

    def test_raises_when_wrong_type(self):
        mock_module = types.SimpleNamespace(server_config="not a config")
        with (
            patch("webcompy.cli._utils.import_module", return_value=mock_module),
            pytest.raises(WebComPyCliException, match="not a ServerConfig"),
        ):
            get_server_config()


class TestGetGenerateConfig:
    def test_returns_default_when_no_module(self):
        config = get_generate_config()
        assert config.dist == "dist"
        assert config.cname == ""
        assert config.static_files_dir == "static"

    def test_returns_config_from_module(self):
        from webcompy.app._config import GenerateConfig

        mock_module = types.SimpleNamespace(generate_config=GenerateConfig(dist="out", cname="example.com"))
        with patch("webcompy.cli._utils.import_module", return_value=mock_module):
            config = get_generate_config()
        assert config.dist == "out"
        assert config.cname == "example.com"

    def test_returns_default_when_no_generate_config_attr(self):
        mock_module = types.SimpleNamespace()
        with patch("webcompy.cli._utils.import_module", return_value=mock_module):
            config = get_generate_config()
        assert config.dist == "dist"

    def test_raises_when_wrong_type(self):
        mock_module = types.SimpleNamespace(generate_config="not a config")
        with (
            patch("webcompy.cli._utils.import_module", return_value=mock_module),
            pytest.raises(WebComPyCliException, match="not a GenerateConfig"),
        ):
            get_generate_config()


class TestDiscoverApp:
    def test_uses_import_path_when_provided(self):
        app = _make_test_app()
        with patch("webcompy.cli._utils.get_app_from_import_path", return_value=app) as mock:
            result = discover_app("my_app.bootstrap:app")
        mock.assert_called_once_with("my_app.bootstrap:app")
        assert result is app

    def test_uses_webcompy_config_when_no_import_path(self):
        app = _make_test_app()
        mock_module = types.SimpleNamespace(app_import_path="my_app.bootstrap:app")
        with (
            patch("webcompy.cli._utils.import_module", return_value=mock_module),
            patch("webcompy.cli._utils.get_app_from_import_path", return_value=app) as mock,
        ):
            result = discover_app(None)
        mock.assert_called_once_with("my_app.bootstrap:app")
        assert result is app

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
