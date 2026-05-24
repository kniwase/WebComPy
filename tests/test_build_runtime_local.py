from __future__ import annotations

import os
import pathlib
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("CI") == "true", reason="Requires external CDN access")

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
E2E_DIR = PROJECT_ROOT / "tests" / "e2e"
TMP_DIR = PROJECT_ROOT / ".tmp" / "e2e-runtime-local-test"


@pytest.fixture(scope="module")
def runtime_local_static_site():
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
            "--runtime-serving",
            "local",
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


def test_runtime_local_static_no_cdn_urls(runtime_local_static_site):
    dist_dir = runtime_local_static_site
    html_content = (dist_dir / "index.html").read_text(encoding="utf-8")
    assert "pyscript.net" not in html_content
    assert "cdn.jsdelivr.net/pyodide" not in html_content


def test_runtime_local_static_assets_exist(runtime_local_static_site):
    dist_dir = runtime_local_static_site
    assert (dist_dir / "_webcompy-assets" / "core.js").exists()
    assert (dist_dir / "_webcompy-assets" / "core.css").exists()
    assert (dist_dir / "_webcompy-assets" / "pyodide" / "pyodide.mjs").exists()
    assert (dist_dir / "_webcompy-assets" / "pyodide" / "pyodide-lock.json").exists()
