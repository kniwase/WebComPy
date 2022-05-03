import os
import pathlib
import shutil
import sys
from tempfile import TemporaryDirectory
from brython.__main__ import main as brython_main  # type: ignore
from webcompy.cli._utils import external_cli_tool_wrapper
from webcompy.cli._exception import WebComPyCliException


@external_cli_tool_wrapper
def install_brython_scripts(dest: str):
    DEST_FILES = {"brython.js", "brython_stdlib.js", "unicode.txt"}
    dest_path = pathlib.Path(dest).absolute()
    if not dest_path.exists():
        os.mkdir(dest_path)
    else:
        for p in (dest_path / n for n in DEST_FILES):
            if p.exists():
                os.remove(p)

    with TemporaryDirectory() as temp_dir:
        temp_dir = pathlib.Path(temp_dir)
        os.chdir(temp_dir)
        sys.argv.append("--install")
        brython_main()
        for child in temp_dir.iterdir():
            if child.name.lower() in DEST_FILES:
                shutil.copy(child, dest_path)
        os.chdir(temp_dir.parent)


@external_cli_tool_wrapper
def make_brython_package(package_dir: str, dest: str):
    if not (package_dir_path := pathlib.Path(package_dir).absolute()).exists():
        raise WebComPyCliException(f"Package dir '{package_dir}' does not exist")
    if not (dest_path := pathlib.Path(dest).absolute()).exists():
        os.mkdir(dest_path)
    package_name = package_dir_path.name
    package_file_name = f"{package_name}.brython.js"
    os.chdir(package_dir_path)
    sys.argv.append("--make_package")
    sys.argv.append(package_name)
    brython_main()
    if (dest_path / package_file_name).exists():
        os.remove(dest_path / package_file_name)
    shutil.move(package_dir_path / package_file_name, dest_path)
