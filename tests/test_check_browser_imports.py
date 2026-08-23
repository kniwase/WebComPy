import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parent.parent / "scripts" / "check-browser-imports.py"


def run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def write(root: Path, name: str, content: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(content)
    return path


def test_clean_module_passes(tmp_path):
    write(
        tmp_path,
        "test_ok.py",
        "\n".join(
            [
                "import pytest",
                "from webcompy.signal import Signal",
                "",
                "",
                "def test_ok():",
                "    import js",
                "",
                "    assert js is not None",
                "",
                "def test_fake_local():",
                "    from webcompy_testing import FakeBrowserDOMPort",
            ]
        ),
    )

    result = run_checker(tmp_path)

    assert result.returncode == 0, result.stderr


def test_top_level_js_import_fails(tmp_path):
    write(tmp_path, "test_bad.py", "import js\n\n\ndef test_x():\n    assert True\n")

    result = run_checker(tmp_path)

    assert result.returncode == 1
    assert "function-local" in result.stderr
    assert "test_bad.py:1" in result.stderr


def test_top_level_pyscript_from_import_fails(tmp_path):
    write(
        tmp_path,
        "test_bad.py",
        "from pyscript import ffi\n\n\ndef test_x():\n    assert True\n",
    )

    result = run_checker(tmp_path)

    assert result.returncode == 1
    assert "pyscript" in result.stderr


def test_top_level_fake_port_import_fails(tmp_path):
    write(
        tmp_path,
        "test_bad.py",
        "from webcompy_testing import FakeBrowserDOMPort\n\n\ndef test_x():\n    assert True\n",
    )

    result = run_checker(tmp_path)

    assert result.returncode == 1
    assert "FakeBrowserDOMPort" in result.stderr


def test_function_local_browser_imports_allowed(tmp_path):
    write(
        tmp_path,
        "test_good.py",
        "\n".join(
            [
                "def test_x():",
                "    from pyodide.http import pyfetch",
                "",
                "    assert pyfetch is not None",
            ]
        ),
    )

    result = run_checker(tmp_path)

    assert result.returncode == 0, result.stderr
