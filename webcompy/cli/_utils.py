from __future__ import annotations

import pathlib
from datetime import datetime
from importlib import import_module

from webcompy.cli._exception import WebComPyCliException
from webcompy.cli.config._build_config import WebComPyBuildConfig


def discover_config(module_path: str | None = None) -> WebComPyBuildConfig:
    if module_path:
        try:
            config_module = import_module(module_path)
        except ModuleNotFoundError:
            raise WebComPyCliException(
                f"No python module named '{module_path}'",
            ) from None
    else:
        try:
            config_module = import_module("webcompy_config")
        except ModuleNotFoundError:
            raise WebComPyCliException(
                "No python module named 'webcompy_config'. Provide --config flag or create webcompy_config.py.",
            ) from None
    config = getattr(config_module, "config", None)
    if config is None:
        raise WebComPyCliException(
            "No 'config' attribute in config module. "
            "Define 'config = WebComPyBuildConfig(app_module, ...)' in the config file.",
        )
    if not isinstance(config, WebComPyBuildConfig):
        raise WebComPyCliException(
            "'config' is not a WebComPyBuildConfig instance",
        )
    return config


def get_webcompy_packge_dir(path: pathlib.Path | None = None) -> pathlib.Path:
    if path is None:
        path = pathlib.Path(__file__)
    if path.is_dir() and path.name == "webcompy":
        return path.absolute()
    else:
        return get_webcompy_packge_dir(path.parent)


def ensure_webcompy_modules_dir(modules_dir: pathlib.Path) -> None:
    modules_dir.mkdir(parents=True, exist_ok=True)
    gitignore = modules_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")


def generate_app_version(app_version: str | None = None) -> str:
    if app_version is not None:
        return app_version
    now = datetime.now()
    return "{}.{}.{}".format(
        now.strftime("%y"),
        now.strftime("%j"),
        (int(now.strftime("%H")) * 60 + int(now.strftime("%M"))) * 60 + int(now.strftime("%S")),
    )
