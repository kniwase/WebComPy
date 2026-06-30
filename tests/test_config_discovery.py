import types
from unittest.mock import patch

import pytest

from webcompy_cli._exception import WebComPyCliException
from webcompy_cli._utils import (
    discover_config,
)
from webcompy_cli.config._build_config import WebComPyBuildConfig


class _FakeModule:
    def __init__(self):
        self.__file__ = __file__
        self.app = None


class TestDiscoverConfig:
    def test_uses_config_path_when_provided(self):
        build_config = WebComPyBuildConfig(app_module=_FakeModule())
        with patch(
            "webcompy_cli._utils.import_module",
            return_value=types.SimpleNamespace(config=build_config),
        ) as mock:
            result = discover_config("my_app.webcompy_config")
        mock.assert_called_once_with("my_app.webcompy_config")
        assert result is build_config

    def test_raises_when_no_module_and_no_config_path(self):
        with (
            patch("webcompy_cli._utils.import_module", side_effect=ModuleNotFoundError),
            pytest.raises(WebComPyCliException, match="webcompy_config"),
        ):
            discover_config(None)

    def test_raises_when_no_config_in_module(self):
        mock_module = types.SimpleNamespace()
        with (
            patch("webcompy_cli._utils.import_module", return_value=mock_module),
            pytest.raises(WebComPyCliException, match="No 'config' attribute"),
        ):
            discover_config(None)

    def test_raises_when_wrong_config_type(self):
        mock_module = types.SimpleNamespace(config="not a config")
        with (
            patch("webcompy_cli._utils.import_module", return_value=mock_module),
            pytest.raises(WebComPyCliException, match="not a WebComPyBuildConfig"),
        ):
            discover_config(None)
