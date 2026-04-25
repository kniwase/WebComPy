import json
from unittest.mock import MagicMock, patch

from webcompy.cli._pyodide_lock import (
    fetch_pyodide_lock,
    get_pyodide_version,
)


class TestGetPyodideVersion:
    def test_known_version(self):
        result = get_pyodide_version("2026.3.1")
        assert result == "0.29.3"

    def test_unknown_version_raises(self):
        try:
            get_pyodide_version("0.0.0")
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "0.0.0" in str(e)


class TestFetchPyodideLock:
    def test_uses_cached_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("webcompy.cli._pyodide_lock.CACHE_DIR", tmp_path)
        lock_data = {"packages": {"numpy": {"version": "2.2.5"}}}
        cached_path = tmp_path / "pyodide-lock-0.29.3.json"
        cached_path.write_text(json.dumps(lock_data), encoding="utf-8")

        with patch("webcompy.cli._pyodide_lock.urllib.request.urlopen") as mock_urlopen:
            result = fetch_pyodide_lock("0.29.3")
            mock_urlopen.assert_not_called()

        assert result is not None
        assert "packages" in result
        assert "numpy" in result["packages"]

    def test_fetches_when_no_cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr("webcompy.cli._pyodide_lock.CACHE_DIR", tmp_path)

        lock_data = {"packages": {"numpy": {"version": "2.2.5"}}}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(lock_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("webcompy.cli._pyodide_lock.urllib.request.urlopen", return_value=mock_response):
            result = fetch_pyodide_lock("0.29.3")

        assert result is not None
        assert "packages" in result
        cached_path = tmp_path / "pyodide-lock-0.29.3.json"
        assert cached_path.exists()

    def test_network_failure_no_cache_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("webcompy.cli._pyodide_lock.CACHE_DIR", tmp_path)

        import urllib.error

        with patch("webcompy.cli._pyodide_lock.urllib.request.urlopen", side_effect=urllib.error.URLError("fail")):
            result = fetch_pyodide_lock("0.99.0")

        assert result is None

    def test_network_failure_with_cache_returns_cached(self, tmp_path, monkeypatch):
        monkeypatch.setattr("webcompy.cli._pyodide_lock.CACHE_DIR", tmp_path)
        lock_data = {"packages": {"numpy": {"version": "2.2.5"}}}
        cached_path = tmp_path / "pyodide-lock-0.29.3.json"
        cached_path.write_text(json.dumps(lock_data), encoding="utf-8")

        import urllib.error

        with patch("webcompy.cli._pyodide_lock.urllib.request.urlopen", side_effect=urllib.error.URLError("fail")):
            result = fetch_pyodide_lock("0.29.3")

        assert result is not None
        assert "packages" in result
