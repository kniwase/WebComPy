import pathlib
import zipfile

import pytest

from webcompy.cli._wheel_builder import get_stable_wheel_filename

E2E_DIR = pathlib.Path(__file__).parent


@pytest.mark.e2e
class TestStaticSiteWheelFilename:
    def test_wheel_filename_matches_html_url(self, static_site):
        dist_dir, wheel_file, app_name = static_site

        expected_filename = get_stable_wheel_filename(app_name)
        assert wheel_file.name == expected_filename, (
            f"Wheel filename {wheel_file.name!r} does not match expected {expected_filename!r}"
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
