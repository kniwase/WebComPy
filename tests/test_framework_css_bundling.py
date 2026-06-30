from __future__ import annotations

import zipfile
from pathlib import Path

from webcompy.cli._wheel_builder import _collect_package_files, _discover_packages


def test_collect_package_files_includes_css() -> None:
    pkg_dir = Path(__file__).resolve().parent.parent / "webcompy"
    packages = _discover_packages(pkg_dir)
    files = _collect_package_files(pkg_dir, packages, None)
    css_files = sorted(arc for _fp, arc in files if arc.endswith(".css"))
    assert "webcompy/ui/_styles/tokens.css" in css_files
    assert "webcompy/ui/_styles/index.css" in css_files
    assert "webcompy/ui/_styles/components.css" in css_files


def test_collect_package_files_still_includes_python() -> None:
    pkg_dir = Path(__file__).resolve().parent.parent / "webcompy"
    packages = _discover_packages(pkg_dir)
    files = _collect_package_files(pkg_dir, packages, None)
    py_files = [arc for _fp, arc in files if arc.endswith(".py")]
    assert "webcompy/__init__.py" in py_files
    assert "webcompy/ui/_styles/__init__.py" in py_files


def test_collect_package_files_still_includes_py_typed() -> None:
    pkg_dir = Path(__file__).resolve().parent.parent / "webcompy"
    packages = _discover_packages(pkg_dir)
    files = _collect_package_files(pkg_dir, packages, None)
    arc_paths = [arc for _fp, arc in files]
    assert "webcompy/py.typed" in arc_paths


def test_browser_wheel_contains_css(tmp_path: Path) -> None:
    from webcompy.cli._wheel_builder import make_browser_webcompy_wheel

    pkg_dir = Path(__file__).resolve().parent.parent / "webcompy"
    wheel_path = make_browser_webcompy_wheel(pkg_dir, tmp_path, "0.0.0-test")
    with zipfile.ZipFile(wheel_path) as zf:
        css_files = sorted(n for n in zf.namelist() if n.endswith(".css"))
    assert "webcompy/ui/_styles/tokens.css" in css_files
    assert "webcompy/ui/_styles/index.css" in css_files
