import pathlib
import re
import zipfile

import pytest

E2E_DIR = pathlib.Path(__file__).parent

_WHEEL_FILENAME_RE = re.compile(r"\w+-0\+sha\.[0-9a-f]{8}-py3-none-any\.whl")


@pytest.mark.e2e
class TestStaticSiteWheelFilename:
    def test_wheel_filename_has_content_hash(self, static_site):
        dist_dir, wheel_file, _app_name = static_site

        assert _WHEEL_FILENAME_RE.match(wheel_file.name), (
            f"Wheel filename {wheel_file.name!r} does not match content-hash pattern"
        )

        html_path = dist_dir / "index.html"
        assert html_path.exists()
        html_content = html_path.read_text(encoding="utf-8")
        assert f"_webcompy-app-package/{wheel_file.name}" in html_content, (
            f"Wheel filename {wheel_file.name!r} not found in HTML. "
            f"Expected URL containing '_webcompy-app-package/{wheel_file.name}'"
        )

    def test_wheel_is_valid_zip(self, static_site):
        _, wheel_file, _ = static_site
        assert zipfile.is_zipfile(wheel_file), f"Wheel file is not a valid zip: {wheel_file}"


@pytest.mark.e2e
class TestSplitModeWheelFilenames:
    def test_framework_wheel_exists(self, split_static_site):
        _dist_dir, _app_wheel, framework_wheel, _app_name, _all_wheels = split_static_site
        assert framework_wheel.exists()
        assert framework_wheel.name == "webcompy-py3-none-any.whl"

    def test_framework_wheel_in_html(self, split_static_site):
        dist_dir, _app_wheel, _framework_wheel, _app_name, _all_wheels = split_static_site
        html_content = (dist_dir / "index.html").read_text(encoding="utf-8")
        assert "_webcompy-app-package/webcompy-py3-none-any.whl" in html_content

    def test_app_wheel_has_content_hash(self, split_static_site):
        _dist_dir, app_wheel, _framework_wheel, _app_name, _all_wheels = split_static_site
        assert _WHEEL_FILENAME_RE.match(app_wheel.name)

    def test_all_wheels_are_valid_zips(self, split_static_site):
        _dist_dir, _app_wheel, _framework_wheel, _app_name, all_wheels = split_static_site
        for wf in all_wheels:
            assert zipfile.is_zipfile(wf), f"Not a valid zip: {wf.name}"
