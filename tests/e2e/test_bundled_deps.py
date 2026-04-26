import json
import pathlib
import zipfile

import pytest

from webcompy.cli._lockfile import LOCKFILE_NAME, load_lockfile
from webcompy.cli._wheel_builder import get_stable_wheel_filename

E2E_DIR = pathlib.Path(__file__).parent


@pytest.mark.e2e
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
        assert "aiofiles" in lockfile.bundled_packages, (
            f"aiofiles not in bundled_packages: {list(lockfile.bundled_packages.keys())}"
        )
        assert lockfile.bundled_packages["aiofiles"].source == "explicit"

    def test_lockfile_has_correct_schema(self, static_site):
        _, _, app_name = static_site
        app_dir = E2E_DIR / app_name
        lockfile_path = app_dir / LOCKFILE_NAME
        data = json.loads(lockfile_path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert "pyodide_version" in data
        assert "pyscript_version" in data
        assert "pyodide_packages" in data
        assert "bundled_packages" in data
        assert "standalone_assets" in data


@pytest.mark.e2e
class TestBundledDepsWheel:
    def test_wheel_contains_bundled_dependency(self, static_site):
        _, wheel_file, _ = static_site
        with zipfile.ZipFile(wheel_file) as zf:
            names = zf.namelist()
            has_aiofiles = any(n.startswith("aiofiles/") for n in names)
            assert has_aiofiles, (
                f"Wheel does not contain aiofiles package. "
                f"Top-level entries: {sorted(n.split('/')[0] for n in names if '/' in names)[:20]}"
            )

    def test_wheel_excludes_cli(self, static_site):
        _, wheel_file, _ = static_site
        with zipfile.ZipFile(wheel_file) as zf:
            names = zf.namelist()
            cli_files = [n for n in names if n.startswith("webcompy/cli/")]
            assert len(cli_files) == 0, f"Wheel contains webcompy/cli/ files: {cli_files[:5]}"

    def test_wheel_top_level_includes_bundled_deps(self, static_site):
        _, wheel_file, _ = static_site
        with zipfile.ZipFile(wheel_file) as zf:
            top_level_entries = [n for n in zf.namelist() if n.endswith("/top_level.txt")]
            assert len(top_level_entries) == 1
            top_level_content = zf.read(top_level_entries[0]).decode()
            top_levels = [line.strip() for line in top_level_content.strip().split("\n") if line.strip()]
            assert "webcompy" in top_levels
            assert "aiofiles" in top_levels, f"aiofiles not in top_level.txt: {top_levels}"

    def test_stable_filename_in_wheel(self, static_site):
        _, wheel_file, app_name = static_site
        expected = f"{app_name.replace('-', '_')}-0-py3-none-any.whl"
        assert wheel_file.name == expected


@pytest.mark.e2e
class TestBundledDepsHTML:
    def test_html_contains_wheel_url(self, static_site):
        dist_dir, _, app_name = static_site
        html_path = dist_dir / "index.html"
        html_content = html_path.read_text(encoding="utf-8")
        expected_url = f"_webcompy-app-package/{get_stable_wheel_filename(app_name)}"
        assert expected_url in html_content

    def test_html_does_not_list_bundled_deps_in_packages(self, static_site):
        dist_dir, _, _ = static_site
        html_path = dist_dir / "index.html"
        html_content = html_path.read_text(encoding="utf-8")
        assert '"aiofiles"' not in html_content, "aiofiles should not appear in py-config.packages (it is bundled)"
