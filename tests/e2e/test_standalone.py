from __future__ import annotations

import os
import pathlib
import shutil
import subprocess

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(os.environ.get("CI") == "true", reason="Requires external CDN access"),
]

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
E2E_DIR = pathlib.Path(__file__).parent
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
    html_content = (standalone_dist / "index.html").read_text(encoding="utf-8")
    assert "/_webcompy-assets/pyodide/pyodide.mjs" in html_content


def test_standalone_static_has_local_lockfile_url(standalone_dist):
    html_content = (standalone_dist / "index.html").read_text(encoding="utf-8")
    assert "/_webcompy-assets/pyodide/pyodide-lock.json" in html_content


def test_standalone_static_runtime_assets_exist(standalone_dist):
    assert (standalone_dist / "_webcompy-assets" / "core.js").exists()
    assert (standalone_dist / "_webcompy-assets" / "core.css").exists()
    assert (standalone_dist / "_webcompy-assets" / "pyodide" / "pyodide.mjs").exists()
