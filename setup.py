import os
import pathlib
from setuptools import setup, find_packages
from pathlib import Path


def _get_files(path: pathlib.Path, suffix: str) -> list[str]:
    ret: list[str] = []
    if path.is_dir():
        for p in path.iterdir():
            ret.extend(_get_files(p, suffix))
    elif path.suffix == suffix:
        ret.append(str(path))
    return ret


package_name = "webcompy"
root_dir = Path(__file__).parent.absolute()

package_dir = root_dir / "webcompy"
pyi_files = [
    p.replace(str(package_dir) + os.sep, "").replace("\\", "/")
    for p in _get_files(package_dir, ".pyi")
]

template_data_dir = package_dir / "cli" / "template_data"
template_files = [
    p.replace(str(package_dir) + os.sep, "").replace("\\", "/")
    for p in _get_files(template_data_dir, ".py")
]

setup(
    name=package_name,
    version="0.0.3",
    description="Python frontend framework which works on Browser",
    long_description=(root_dir / "README.md").open("r", encoding="utf8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/kniwase/WebComPy",
    author="Kento Niwase",
    author_email="kento.niwase@outlook.com",
    license="MIT",
    keywords="browser,frontend,framework,front-end,client-side",
    packages=find_packages(exclude=["docs_src", "template"]),
    package_data={
        "webcompy": [
            "py.typed",
            *pyi_files,
            *template_files,
        ],
    },
    install_requires=[
        name.rstrip()
        for name in (root_dir / "requirements.txt")
        .open("r", encoding="utf8")
        .readlines()
    ],
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
