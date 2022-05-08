from importlib import import_module
import os
import pathlib
import sys
from typing import Callable, ParamSpec, TypeVar
from webcompy.cli._config import WebComPyConfig
from webcompy.cli._exception import WebComPyCliException
from webcompy.app._app import WebComPyApp


def get_config() -> WebComPyConfig:
    try:
        webcompy_config = import_module("webcompy_config")
    except ModuleNotFoundError:
        raise WebComPyCliException(
            "No python module named 'webcompy_config'",
        )
    configs = tuple(
        it
        for name in dir(webcompy_config)
        if isinstance(it := getattr(webcompy_config, name), WebComPyConfig)
    )
    if len(configs) == 0:
        raise WebComPyCliException(
            "No WebComPyConfig instance in 'webcompy_config.py'",
        )
    elif len(configs) == 0:
        raise WebComPyCliException(
            "Multiple WebComPyConfig instances in 'webcompy_config.py'"
        )
    else:
        config = configs[0]
    return config


def get_app(config: WebComPyConfig) -> WebComPyApp:
    try:
        import_module(config.app_package)
    except ModuleNotFoundError:
        raise WebComPyCliException(
            f"No python module named '{config.app_package}'",
        )
    try:
        bootstrap = import_module(config.app_package + ".bootstrap")
    except AttributeError:
        raise WebComPyCliException(
            f"No python module named 'bootstrap' in '{config.app_package}'",
        )
    app_instances = tuple(
        it
        for name in dir(bootstrap)
        if isinstance(it := getattr(bootstrap, name), WebComPyApp)
    )
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


def get_webcompy_packge_dir(path: pathlib.Path | None = None) -> str:
    if path is None:
        path = pathlib.Path(__file__)
    if path.is_dir() and path.name == "webcompy":
        return str(path.absolute())
    else:
        return get_webcompy_packge_dir(path.parent)


P = ParamSpec("P")
T = TypeVar("T")


def external_cli_tool_wrapper(func: Callable[P, T]) -> Callable[P, T]:
    def inner(*args: P.args, **kwargs: P.kwargs):
        cwd_ori = pathlib.Path.cwd()
        argv_ori = tuple(sys.argv[1:])
        for _ in range(1, len(sys.argv)):
            sys.argv.pop(1)
        ret = func(*args, **kwargs)
        for _ in range(1, len(sys.argv)):
            sys.argv.pop(1)
        for arg in argv_ori:
            sys.argv.append(arg)
        os.chdir(cwd_ori)
        return ret

    return inner
