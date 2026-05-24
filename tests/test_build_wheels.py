import json
import pathlib
import re
import zipfile

import pytest

from webcompy.cli._lockfile import LOCKFILE_NAME, load_lockfile

E2E_DIR = pathlib.Path(__file__).parent / "e2e"

_WHEEL_FILENAME_RE = re.compile(r"\w+-0\+sha\.[0-9a-f]{8}-py3-none-any\.whl")


@pytest.fixture(scope="module")
def static_site():
    import os
    import shutil
    import subprocess

    PROJECT_ROOT = pathlib.Path(__file__).parent.parent
    TMP_DIR = PROJECT_ROOT / ".tmp" / "e2e-build-test"

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True)

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
        ],
        cwd=str(E2E_DIR),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Generate failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    assert dist_dir.exists()

    wheel_dir = dist_dir / "_webcompy-app-package"
    assert wheel_dir.exists()

    wheel_files = list(wheel_dir.glob("*.whl"))
    assert len(wheel_files) >= 1

    app_dir = E2E_DIR / "my_app"
    yield dist_dir, wheel_files[0], app_dir.name

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)


class TestBundledDepsLockfile:
    def test_lockfile_exists(self, static_site):
        _, _, app_name = static_site
        app_dir = E2E_DIR / app_name
        lockfile_path = app_dir / LOCKFILE_NAME
        assert lockfile_path.exists(), f"Lock file not found at {lockfile_path}"

    def test_lockfile_contains_bundled_packages(self, static_site):
        _, _, app_name = static_site
        app_dir = E2E_DIR / app_name
        lockfile_path = app_dir / LOCKFILE_NAME
        lockfile = load_lockfile(lockfile_path)
        assert lockfile is not None
        assert "aiofiles" in lockfile.pure_python_packages
        assert lockfile.pure_python_packages["aiofiles"].source == "explicit"

    def test_lockfile_has_correct_schema(self, static_site):
        _, _, app_name = static_site
        app_dir = E2E_DIR / app_name
        lockfile_path = app_dir / LOCKFILE_NAME
        data = json.loads(lockfile_path.read_text(encoding="utf-8"))
        assert data["version"] == 2
        assert "pyodide_version" in data
        assert "pyscript_version" in data
        assert "wasm_packages" in data
        assert "pure_python_packages" in data


class TestBundledDepsWheel:
    def test_wheel_contains_bundled_dependency(self, static_site):
        _, wheel_file, _ = static_site
        with zipfile.ZipFile(wheel_file) as zf:
            names = zf.namelist()
            has_aiofiles = any(n.startswith("aiofiles/") for n in names)
            assert has_aiofiles

    def test_wheel_excludes_cli(self, static_site):
        _, wheel_file, _ = static_site
        with zipfile.ZipFile(wheel_file) as zf:
            names = zf.namelist()
            cli_files = [n for n in names if n.startswith("webcompy/cli/")]
            assert len(cli_files) == 0

    def test_wheel_top_level_includes_bundled_deps(self, static_site):
        _, wheel_file, _ = static_site
        with zipfile.ZipFile(wheel_file) as zf:
            top_level_entries = [n for n in zf.namelist() if n.endswith("/top_level.txt")]
            assert len(top_level_entries) == 1
            top_level_content = zf.read(top_level_entries[0]).decode()
            top_levels = [line.strip() for line in top_level_content.strip().split("\n") if line.strip()]
            assert "webcompy" in top_levels
            assert "aiofiles" in top_levels

    def test_wheel_filename_has_content_hash(self, static_site):
        _, wheel_file, _ = static_site
        assert _WHEEL_FILENAME_RE.match(wheel_file.name)


class TestBundledDepsHTML:
    def test_html_contains_wheel_url(self, static_site):
        dist_dir, wheel_file, _ = static_site
        html_content = (dist_dir / "index.html").read_text(encoding="utf-8")
        expected_url = f"_webcompy-app-package/{wheel_file.name}"
        assert expected_url in html_content

    def test_html_does_not_list_bundled_deps_in_packages(self, static_site):
        dist_dir, _, _ = static_site
        html_content = (dist_dir / "index.html").read_text(encoding="utf-8")
        assert '"aiofiles"' not in html_content


class TestStaticSiteWheel:
    def test_wheel_filename_has_content_hash(self, static_site):
        dist_dir, wheel_file, _app_name = static_site
        assert _WHEEL_FILENAME_RE.match(wheel_file.name)
        html_content = (dist_dir / "index.html").read_text(encoding="utf-8")
        assert f"_webcompy-app-package/{wheel_file.name}" in html_content

    def test_wheel_is_valid_zip(self, static_site):
        _, wheel_file, _ = static_site
        assert zipfile.is_zipfile(wheel_file)
