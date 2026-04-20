from __future__ import annotations

import importlib
import pathlib
from datetime import datetime
from importlib import import_module

from webcompy.app._app import WebComPyApp
from webcompy.app._config import GenerateConfig, ServerConfig
from webcompy.cli._exception import WebComPyCliException


def get_app_from_import_path(import_path: str) -> WebComPyApp:
    if ":" not in import_path:
        raise WebComPyCliException(
            f"Invalid app import path '{import_path}'. Expected format: 'module.path:variable_name'",
        )
    module_path, var_name = import_path.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError:
        raise WebComPyCliException(
            f"No python module named '{module_path}'",
        ) from None
    app = getattr(module, var_name, None)
    if app is None:
        raise WebComPyCliException(
            f"No attribute '{var_name}' in module '{module_path}'",
        )
    if not isinstance(app, WebComPyApp):
        raise WebComPyCliException(
            f"'{import_path}' is not a WebComPyApp instance",
        )
    return app


def _extract_package(import_path: str) -> str | None:
    if ":" not in import_path:
        raise WebComPyCliException(
            f"Invalid app import path '{import_path}'. Expected format: 'module.path:variable_name'",
        )
    module_path = import_path.rsplit(":", 1)[0]
    parts = module_path.rsplit(".", 1)
    if len(parts) == 1:
        return None
    return parts[0]


def discover_app(
    app_import_path: str | None = None,
) -> tuple[WebComPyApp, str | None]:
    if app_import_path:
        package = _extract_package(app_import_path)
        return get_app_from_import_path(app_import_path), package
    try:
        webcompy_config = import_module("webcompy_config")
    except ModuleNotFoundError:
        raise WebComPyCliException(
            "No python module named 'webcompy_config'. "
            "Provide --app flag or create webcompy_config.py with app_import_path.",
        ) from None
    app_import_path_value = getattr(webcompy_config, "app_import_path", None)
    if app_import_path_value is None:
        raise WebComPyCliException(
            "No 'app_import_path' in 'webcompy_config.py'",
        )
    package = _extract_package(app_import_path_value)
    return get_app_from_import_path(app_import_path_value), package


def _import_config_module(module_name: str):
    try:
        return import_module(module_name)
    except ModuleNotFoundError:
        return None


def get_server_config(package: str | None = None) -> ServerConfig:
    for prefix in ([package] if package else []) + [None]:
        module_name = f"{prefix}.webcompy_server_config" if prefix else "webcompy_server_config"
        module = _import_config_module(module_name)
        if module is None:
            continue
        server_config = getattr(module, "server_config", None)
        if server_config is None:
            continue
        if not isinstance(server_config, ServerConfig):
            raise WebComPyCliException(
                f"'server_config' in '{module_name}' is not a ServerConfig instance",
            )
        return server_config
    return ServerConfig()


def get_generate_config(package: str | None = None) -> GenerateConfig:
    for prefix in ([package] if package else []) + [None]:
        module_name = f"{prefix}.webcompy_server_config" if prefix else "webcompy_server_config"
        module = _import_config_module(module_name)
        if module is None:
            continue
        generate_config = getattr(module, "generate_config", None)
        if generate_config is None:
            continue
        if not isinstance(generate_config, GenerateConfig):
            raise WebComPyCliException(
                f"'generate_config' in '{module_name}' is not a GenerateConfig instance",
            )
        return generate_config
    return GenerateConfig()


def get_webcompy_packge_dir(path: pathlib.Path | None = None) -> pathlib.Path:
    if path is None:
        path = pathlib.Path(__file__)
    if path.is_dir() and path.name == "webcompy":
        return path.absolute()
    else:
        return get_webcompy_packge_dir(path.parent)


def generate_app_version():
    now = datetime.now()
    return "{}.{}.{}".format(
        now.strftime("%y"),
        now.strftime("%j"),
        (int(now.strftime("%H")) * 60 + int(now.strftime("%M"))) * 60 + int(now.strftime("%S")),
    )
