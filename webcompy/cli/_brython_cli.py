import os
import pathlib
import shutil
import sys
from tempfile import TemporaryDirectory
from brython.__main__ import main as brython_main  # type: ignore
from webcompy.cli._utils import external_cli_tool_wrapper
from webcompy.cli._exception import WebComPyCliException


@external_cli_tool_wrapper
def install_brython_scripts(dest: pathlib.Path):
    DEST_FILES = {"brython.js", "brython_stdlib.js", "unicode.txt"}
    dest_abs = dest.absolute()
    if not dest_abs.exists():
        os.mkdir(dest_abs)
    else:
        for p in (dest_abs / n for n in DEST_FILES):
            if p.exists():
                os.remove(p)

    with TemporaryDirectory() as temp_dir:
        temp_dir = pathlib.Path(temp_dir)
        os.chdir(temp_dir)
        sys.argv.append("--install")
        brython_main()
        for child in temp_dir.iterdir():
            if child.name.lower() in DEST_FILES:
                shutil.copy(child, dest_abs)
        os.chdir(temp_dir.parent)


@external_cli_tool_wrapper
def make_brython_package(package_dir: pathlib.Path, dest: pathlib.Path):
    if not (package_dir_abs := package_dir.absolute()).exists():
        raise WebComPyCliException(f"Package dir '{package_dir}' does not exist")
    if not (dest_abs := dest.absolute()).exists():
        os.mkdir(dest_abs)
    package_name = package_dir_abs.name
    package_file_name = f"{package_name}.brython.js"
    os.chdir(package_dir_abs)
    sys.argv.append("--make_package")
    sys.argv.append(package_name)
    brython_main()
    if (dest_abs / package_file_name).exists():
        os.remove(dest_abs / package_file_name)
    shutil.move(package_dir_abs / package_file_name, dest_abs)


def make_webcompy_app_package_brython(
    dest: pathlib.Path,
    webcompy_package_dir: pathlib.Path,
    package_dir: pathlib.Path,
):
    install_brython_scripts(dest)
    make_brython_package(webcompy_package_dir, dest)
    make_brython_package(package_dir, dest)
