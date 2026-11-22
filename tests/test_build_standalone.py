from __future__ import annotations

import os
import pathlib
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("CI") == "true", reason="Requires external CDN access")

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
E2E_DIR = PROJECT_ROOT / "e2e" / "core"
TMP_DIR = PROJECT_ROOT / ".tmp" / "e2e-standalone"


@pytest.fixture(scope="module")
def standalone_dist():
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(E2E_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    dist_dir = TMP_DIR / "dist"

    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT),
            "python",
            "-m",
            "webcompy",
            "generate",
            "--dist",
            str(dist_dir),
            "--standalone",
        ],
        cwd=str(E2E_DIR),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Generate failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    yield dist_dir

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)


def test_standalone_static_no_cdn_urls(standalone_dist):
    html_content = (standalone_dist / "index.html").read_text(encoding="utf-8")
    assert "pyscript.net" not in html_content
    assert "cdn.jsdelivr.net/pyodide" not in html_content


def test_standalone_static_has_local_interpreter(standalone_dist):
    from webcompy_server._html import PYSCRIPT_VERSION

    html_content = (standalone_dist / "index.html").read_text(encoding="utf-8")
    assert f"/_webcompy-assets/{PYSCRIPT_VERSION}/pyodide/pyodide.mjs" in html_content


def test_standalone_static_has_local_lockfile_url(standalone_dist):
    from webcompy_server._html import PYSCRIPT_VERSION

    html_content = (standalone_dist / "index.html").read_text(encoding="utf-8")
    assert f"/_webcompy-assets/{PYSCRIPT_VERSION}/pyodide/pyodide-lock.json" in html_content


def test_standalone_static_runtime_assets_exist(standalone_dist):
    from webcompy_server._html import PYSCRIPT_VERSION

    version_dir = standalone_dist / "_webcompy-assets" / PYSCRIPT_VERSION
    assert (version_dir / "core.js").exists()
    assert (version_dir / "core.css").exists()
    assert (version_dir / "pyodide" / "pyodide.mjs").exists()
    assert not (standalone_dist / "_webcompy-assets" / "core.js").exists()
