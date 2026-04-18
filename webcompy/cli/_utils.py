from __future__ import annotations

import pathlib
from datetime import datetime
from importlib import import_module

from webcompy.app._app import WebComPyApp
from webcompy.cli._config import WebComPyConfig
from webcompy.cli._exception import WebComPyCliException


def get_config() -> WebComPyConfig:
    try:
        webcompy_config = import_module("webcompy_config")
    except ModuleNotFoundError:
        raise WebComPyCliException(
            "No python module named 'webcompy_config'",
        ) from None
    configs = tuple(
        it for name in dir(webcompy_config) if isinstance(it := getattr(webcompy_config, name), WebComPyConfig)
    )
    if len(configs) == 0:
        raise WebComPyCliException(
            "No WebComPyConfig instance in 'webcompy_config.py'",
        )
    elif len(configs) == 0:
        raise WebComPyCliException("Multiple WebComPyConfig instances in 'webcompy_config.py'")
    else:
        config = configs[0]
    return config


def get_app(config: WebComPyConfig) -> WebComPyApp:
    try:
        import_module(config.app_package_path.name)
    except ModuleNotFoundError:
        raise WebComPyCliException(
            f"No python module named '{config.app_package_path.name}'",
        ) from None
    try:
        bootstrap = import_module(config.app_package_path.name + ".bootstrap")
    except AttributeError:
        raise WebComPyCliException(
            f"No python module named 'bootstrap' in '{config.app_package_path.name}'",
        ) from None
    app_instances = tuple(it for name in dir(bootstrap) if isinstance(it := getattr(bootstrap, name), WebComPyApp))
    if len(app_instances) == 0:
        raise WebComPyCliException(
            "No WebComPyApp instance in 'bootstrap.py'",
        )
    elif len(app_instances) == 0:
        raise WebComPyCliException(
            "Multiple WebComPyApp instances in 'bootstrap.py'",
        )
    else:
        app = app_instances[0]
    return app


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
