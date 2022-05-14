from functools import partial
import os
import pathlib
from re import compile as re_complie, escape as re_escape
from webcompy.cli._exception import WebComPyCliException


def _list_up_files(target: pathlib.Path) -> list[pathlib.Path]:
    if target.is_dir():
        return [f for d in target.iterdir() for f in _list_up_files(d)]
    else:
        return [target]


def get_static_files(static_file_dir: pathlib.Path):
    static_file_dir = static_file_dir.absolute()
    if not static_file_dir.exists():
        raise WebComPyCliException(
            f"Static File dir '{static_file_dir}' does not exist"
        )
    elif not static_file_dir.is_dir():
        raise WebComPyCliException(
            f"'{static_file_dir}' is not directory",
        )
    get_relative_path = partial(
        re_complie("^" + re_escape(str(static_file_dir) + os.sep)).sub, ""
    )
    return tuple(
        get_relative_path(str(p)).replace("\\", "/")
        for p in _list_up_files(static_file_dir)
    )
