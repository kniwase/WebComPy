import os
import pathlib
import shutil
import sys
from setuptools import setup, find_packages
from tempfile import TemporaryDirectory
from webcompy.cli._utils import external_cli_tool_wrapper
from webcompy.cli._exception import WebComPyCliException


@external_cli_tool_wrapper
def make_wheel(name: str, package_dir: pathlib.Path, dest: pathlib.Path):
    if not (package_dir_path := package_dir.absolute()).exists():
        raise WebComPyCliException(f"Package dir '{package_dir}' does not exist")
    if not (dest_path := dest.absolute()).exists():
        os.mkdir(dest_path)
    wheel_file_name = f"{name}-0.0.0-py3-none-any.whl"
    with TemporaryDirectory() as temp:
        temp = pathlib.Path(temp)
        wheel_temp = pathlib.Path(temp)
        cwd = pathlib.Path.cwd()
        os.chdir(temp)
        sys.argv.extend(
            [
                "--no-user-cfg",
                "--quiet",
                "bdist_wheel",
                "--dist-dir",
                str(wheel_temp),
            ]
        )
        try:
            wheel_temp_dest = wheel_temp / wheel_file_name
            if wheel_temp_dest.exists():
                os.remove(wheel_temp_dest)
            packages = find_packages(
                where=str(package_dir_path.parent),
                include=[package_dir_path.name, f"{package_dir_path.name}.*"],
                exclude=["__pycache__"],
            )
            setup(
                name=name,
                packages=packages,
                package_dir={
                    p: str(package_dir_path.parent / p.replace(".", "/"))
                    for p in packages
                },
            )
            wheel_dest = dest_path / wheel_file_name
            if wheel_dest.exists():
                os.remove(wheel_dest)
            wheel_file_path = tuple(
                it
                for it in wheel_temp.iterdir()
                if it.is_file() and it.name == wheel_file_name
            )[0]
            shutil.copy(wheel_file_path, wheel_dest)
        except Exception as error:
            raise error
        finally:
            os.chdir(cwd)


def make_webcompy_app_package_pyscript(
    dest: pathlib.Path,
    webcompy_package_dir: pathlib.Path,
    package_dir: pathlib.Path,
):
    make_wheel("webcompy", webcompy_package_dir, dest)
    make_wheel("app", package_dir, dest)
