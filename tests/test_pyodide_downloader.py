import hashlib
import zipfile
from unittest.mock import patch

import pytest

from webcompy.cli._pyodide_downloader import (
    PyodideDownloadError,
    _sha256_of_file,
    download_pyodide_wheel,
    extract_wheel,
)


class TestSha256OfFile:
    def test_correct_hash(self, tmp_path):
        content = b"hello world"
        expected = hashlib.sha256(content).hexdigest()
        p = tmp_path / "test.bin"
        p.write_bytes(content)
        assert _sha256_of_file(p) == expected

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.bin"
        p.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert _sha256_of_file(p) == expected


class TestDownloadPyodideWheel:
    def test_cache_hit_with_matching_sha256(self, tmp_path, monkeypatch):
        content = b"fake wheel data"
        expected_sha256 = hashlib.sha256(content).hexdigest()
        cache_dir = tmp_path / "cache" / "0.29.3"
        cache_dir.mkdir(parents=True)
        wheel_path = cache_dir / "test-1.0-py3-none-any.whl"
        wheel_path.write_bytes(content)

        monkeypatch.setattr("webcompy.cli._pyodide_downloader.CACHE_DIR", tmp_path / "cache")

        result = download_pyodide_wheel("test-1.0-py3-none-any.whl", "0.29.3", expected_sha256)
        assert result == wheel_path

    def test_sha256_mismatch_raises_error(self, tmp_path, monkeypatch):
        content = b"fake wheel data"
        cache_dir = tmp_path / "cache" / "0.29.3"
        cache_dir.mkdir(parents=True)
        wheel_path = cache_dir / "test-1.0-py3-none-any.whl"
        wheel_path.write_bytes(content)

        monkeypatch.setattr("webcompy.cli._pyodide_downloader.CACHE_DIR", tmp_path / "cache")

        fake_download = b"corrupted data"
        with patch("webcompy.cli._pyodide_downloader.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = lambda s: s
            mock_urlopen.return_value.__exit__ = lambda s, *a: None
            mock_urlopen.return_value.read.return_value = fake_download

            with pytest.raises(PyodideDownloadError, match="SHA256 verification failed"):
                download_pyodide_wheel("test-1.0-py3-none-any.whl", "0.29.3", "wrong_hash")

    def test_network_failure_raises_error(self, tmp_path, monkeypatch):
        import urllib.error

        monkeypatch.setattr("webcompy.cli._pyodide_downloader.CACHE_DIR", tmp_path / "cache_not_exist")

        with patch("webcompy.cli._pyodide_downloader.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("network error")

            with pytest.raises(PyodideDownloadError, match="Failed to download"):
                download_pyodide_wheel("test-1.0-py3-none-any.whl", "0.29.3", "abc123")

    def test_downloads_and_saves_to_cache(self, tmp_path, monkeypatch):
        content = b"downloaded wheel data"
        expected_sha256 = hashlib.sha256(content).hexdigest()

        monkeypatch.setattr("webcompy.cli._pyodide_downloader.CACHE_DIR", tmp_path / "cache")

        with patch("webcompy.cli._pyodide_downloader.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = lambda s: s
            mock_urlopen.return_value.__exit__ = lambda s, *a: None
            mock_urlopen.return_value.read.return_value = content

            result = download_pyodide_wheel("test-1.0-py3-none-any.whl", "0.29.3", expected_sha256)

            assert result.exists()
            assert result.read_bytes() == content


class TestExtractWheel:
    def _create_wheel(self, tmp_path, name="mypackage", version="1.0.0"):
        pkg_dir = tmp_path / name
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("x = 1")
        (pkg_dir / "mod.py").write_text("y = 2")

        dist_name = name.replace("-", "_")
        dist_info = f"{dist_name}-{version}.dist-info"
        wheel_path = tmp_path / f"{name}-{version}-py3-none-any.whl"

        with zipfile.ZipFile(wheel_path, "w") as zf:
            zf.writestr(f"{name}/__init__.py", "x = 1")
            zf.writestr(f"{name}/mod.py", "y = 2")
            zf.writestr(f"{dist_info}/METADATA", f"Name: {name}\nVersion: {version}\n")
            zf.writestr(f"{dist_info}/WHEEL", "Wheel-Version: 1.0\n")
            zf.writestr(f"{dist_info}/top_level.txt", f"{name}\n")
            zf.writestr(f"{dist_info}/RECORD", "")

        return wheel_path

    def test_extract_wheel_returns_package_names(self, tmp_path):
        wheel_path = self._create_wheel(tmp_path)
        dest = tmp_path / "extracted"
        dest.mkdir()

        result = extract_wheel(wheel_path, dest)

        assert len(result) > 0
        pkg_names = [name for name, _ in result]
        assert "mypackage" in pkg_names

    def test_extracted_files_exist(self, tmp_path):
        wheel_path = self._create_wheel(tmp_path)
        dest = tmp_path / "extracted"
        dest.mkdir()

        extract_wheel(wheel_path, dest)

        assert (dest / "mypackage" / "__init__.py").exists()
        assert (dest / "mypackage" / "mod.py").exists()
