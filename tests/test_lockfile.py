from __future__ import annotations

import json

from webcompy.cli._lockfile import (
    Lockfile,
    PurePythonPackageEntry,
    RuntimeAssetEntry,
    WasmPackageEntry,
    get_bundled_deps,
    get_cdn_pure_python_package_names,
    get_wasm_package_names,
    load_lockfile,
    save_lockfile,
    validate_local_environment,
    validate_lockfile,
)


class TestWasmPackageEntry:
    def test_to_dict_without_sha256(self):
        entry = WasmPackageEntry(
            version="2.2.5",
            file_name="numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
            source="explicit",
        )
        d = entry.to_dict()
        assert d == {
            "version": "2.2.5",
            "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
            "source": "explicit",
        }
        assert "sha256" not in d

    def test_to_dict_with_sha256(self):
        entry = WasmPackageEntry(
            version="2.2.5",
            file_name="numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
            source="explicit",
            sha256="abc123def456",
        )
        d = entry.to_dict()
        assert d["sha256"] == "abc123def456"

    def test_from_dict_without_sha256(self):
        data = {
            "version": "2.2.5",
            "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
        }
        entry = WasmPackageEntry.from_dict(data)
        assert entry.version == "2.2.5"
        assert entry.file_name == "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl"
        assert entry.source == "explicit"
        assert entry.sha256 is None

    def test_from_dict_with_sha256(self):
        data = {
            "version": "2.2.5",
            "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
            "sha256": "abc123def456",
        }
        entry = WasmPackageEntry.from_dict(data)
        assert entry.sha256 == "abc123def456"

    def test_from_dict_with_source(self):
        data = {"version": "2.2.5", "file_name": "numpy.whl", "source": "transitive"}
        entry = WasmPackageEntry.from_dict(data)
        assert entry.source == "transitive"
        assert entry.sha256 is None


class TestPurePythonPackageEntry:
    def test_to_dict_cdn(self):
        entry = PurePythonPackageEntry(
            version="0.28.1",
            source="explicit",
            in_pyodide_cdn=True,
            pyodide_file_name="httpx-0.28.1-py3-none-any.whl",
            pyodide_sha256="abc123",
        )
        d = entry.to_dict()
        assert d["version"] == "0.28.1"
        assert d["source"] == "explicit"
        assert d["in_pyodide_cdn"] is True
        assert d["pyodide_file_name"] == "httpx-0.28.1-py3-none-any.whl"
        assert d["pyodide_sha256"] == "abc123"

    def test_to_dict_local_only(self):
        entry = PurePythonPackageEntry(
            version="3.1.0",
            source="explicit",
            in_pyodide_cdn=False,
        )
        d = entry.to_dict()
        assert d["version"] == "3.1.0"
        assert d["in_pyodide_cdn"] is False
        assert "pyodide_file_name" not in d
        assert "pyodide_sha256" not in d

    def test_from_dict_cdn(self):
        data = {
            "version": "0.28.1",
            "source": "explicit",
            "in_pyodide_cdn": True,
            "pyodide_file_name": "httpx-0.28.1-py3-none-any.whl",
            "pyodide_sha256": "abc123",
        }
        entry = PurePythonPackageEntry.from_dict(data)
        assert entry.version == "0.28.1"
        assert entry.in_pyodide_cdn is True
        assert entry.pyodide_file_name == "httpx-0.28.1-py3-none-any.whl"
        assert entry.pyodide_sha256 == "abc123"

    def test_from_dict_local_only(self):
        data = {"version": "3.1.0", "source": "explicit", "in_pyodide_cdn": False}
        entry = PurePythonPackageEntry.from_dict(data)
        assert entry.in_pyodide_cdn is False
        assert entry.pyodide_file_name is None
        assert entry.pyodide_sha256 is None


class TestLockfileV2:
    def test_roundtrip(self, tmp_path):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            wasm_serving="cdn",
            wasm_packages={
                "numpy": WasmPackageEntry(
                    version="2.2.5",
                    file_name="numpy.whl",
                    sha256="abc123",
                    source="explicit",
                ),
            },
            pure_python_packages={
                "httpx": PurePythonPackageEntry(
                    version="0.28.1",
                    source="explicit",
                    in_pyodide_cdn=True,
                    pyodide_file_name="httpx-0.28.1-py3-none-any.whl",
                    pyodide_sha256="def456",
                ),
                "flask": PurePythonPackageEntry(
                    version="3.1.0",
                    source="explicit",
                    in_pyodide_cdn=False,
                ),
            },
        )
        path = tmp_path / "webcompy-lock.json"
        save_lockfile(lockfile, path)
        loaded = load_lockfile(path)
        assert loaded is not None
        assert loaded.pyodide_version == "0.29.3"
        assert loaded.wasm_serving == "cdn"
        assert "numpy" in loaded.wasm_packages
        assert loaded.wasm_packages["numpy"].sha256 == "abc123"
        assert "httpx" in loaded.pure_python_packages
        assert "flask" in loaded.pure_python_packages
        assert loaded.runtime_serving == "cdn"
        assert loaded.runtime_assets == {}

    def test_load_nonexistent_file_returns_none(self, tmp_path):
        result = load_lockfile(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_invalid_json_returns_none(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        assert load_lockfile(path) is None

    def test_load_v1_lockfile_returns_none(self, tmp_path):
        data = {
            "version": 1,
            "pyodide_version": "0.24.0",
            "pyscript_version": "2024.1.1",
            "pyodide_packages": {},
            "bundled_packages": {},
        }
        path = tmp_path / "v1-lock.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        assert load_lockfile(path) is None


class TestValidateLockfile:
    def test_valid_lockfile(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            wasm_packages={
                "numpy": WasmPackageEntry(version="2.2.5", file_name="numpy.whl", source="explicit"),
            },
            pure_python_packages={
                "flask": PurePythonPackageEntry(version="3.1.0", source="explicit", in_pyodide_cdn=False),
            },
        )
        issues = validate_lockfile(lockfile, ["numpy", "flask"])
        assert len(issues) == 0

    def test_missing_dependency(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pure_python_packages={
                "flask": PurePythonPackageEntry(version="3.1.0", source="explicit", in_pyodide_cdn=False),
            },
        )
        issues = validate_lockfile(lockfile, ["flask", "numpy"])
        assert len(issues) > 0
        assert "numpy" in issues[0]


class TestGetWasmPackageNames:
    def test_returns_wasm_names(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            wasm_packages={
                "numpy": WasmPackageEntry(version="2.2.5", file_name="numpy.whl", source="explicit"),
                "scipy": WasmPackageEntry(version="1.14.1", file_name="scipy.whl", source="explicit"),
            },
            pure_python_packages={
                "httpx": PurePythonPackageEntry(version="0.28.1", source="explicit", in_pyodide_cdn=True),
            },
        )
        result = get_wasm_package_names(lockfile)
        assert result == ["numpy", "scipy"]

    def test_returns_empty_for_none(self):
        assert get_wasm_package_names(None) == []


class TestGetCdnPurePythonPackageNames:
    def test_returns_cdn_names(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pure_python_packages={
                "httpx": PurePythonPackageEntry(version="0.28.1", source="explicit", in_pyodide_cdn=True),
                "flask": PurePythonPackageEntry(version="3.1.0", source="explicit", in_pyodide_cdn=False),
            },
        )
        result = get_cdn_pure_python_package_names(lockfile)
        assert result == ["httpx"]

    def test_returns_empty_for_none(self):
        assert get_cdn_pure_python_package_names(None) == []


class TestGetBundledDeps:
    def test_serve_all_deps_true_returns_local_only(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            wasm_packages={
                "numpy": WasmPackageEntry(version="2.2.5", file_name="numpy.whl", source="explicit"),
            },
            pure_python_packages={
                "httpx": PurePythonPackageEntry(version="0.28.1", source="explicit", in_pyodide_cdn=True),
                "webcompy": PurePythonPackageEntry(version="0.1.0", source="explicit", in_pyodide_cdn=False),
            },
        )
        result = get_bundled_deps(lockfile, serve_all_deps=True)
        assert any(name == "webcompy" for name, _ in result)
        assert not any(name == "httpx" for name, _ in result)
        assert not any(name == "numpy" for name, _ in result)

    def test_serve_all_deps_false_returns_local_only(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pure_python_packages={
                "httpx": PurePythonPackageEntry(version="0.28.1", source="explicit", in_pyodide_cdn=True),
                "webcompy": PurePythonPackageEntry(version="0.1.0", source="explicit", in_pyodide_cdn=False),
            },
        )
        result = get_bundled_deps(lockfile, serve_all_deps=False)
        assert any(name == "webcompy" for name, _ in result)
        assert not any(name == "httpx" for name, _ in result)

    def test_returns_empty_for_none(self):
        assert get_bundled_deps(None) == []


class TestValidateLocalEnvironment:
    def test_cdn_available_not_installed_locally_warns(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pure_python_packages={
                "nonexistent_package_xyz_12345": PurePythonPackageEntry(
                    version="9.9.9", source="explicit", in_pyodide_cdn=True
                ),
            },
        )
        errors, warnings = validate_local_environment(lockfile, serve_all_deps=True)
        assert len(errors) == 0
        assert any("nonexistent_package_xyz_12345" in w for w in warnings)

    def test_local_only_not_installed_errors(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pure_python_packages={
                "nonexistent_package_xyz_12345": PurePythonPackageEntry(
                    version="9.9.9", source="explicit", in_pyodide_cdn=False
                ),
            },
        )
        errors, _warnings = validate_local_environment(lockfile, serve_all_deps=True)
        assert len(errors) > 0
        assert any("nonexistent_package_xyz_12345" in e for e in errors)

    def test_cdn_installed_with_version_mismatch_warns(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pure_python_packages={
                "webcompy": PurePythonPackageEntry(version="99.0.0", source="explicit", in_pyodide_cdn=True),
            },
        )
        errors, warnings = validate_local_environment(lockfile, serve_all_deps=True)
        assert len(errors) == 0
        assert any("version mismatch" in w for w in warnings)

    def test_local_only_version_mismatch_errors(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pure_python_packages={
                "webcompy": PurePythonPackageEntry(version="99.0.0", source="explicit", in_pyodide_cdn=False),
            },
        )
        errors, _warnings = validate_local_environment(lockfile, serve_all_deps=True)
        assert len(errors) > 0
        assert any("version mismatch" in e for e in errors)


class TestRuntimeAssetEntry:
    def test_to_dict(self):
        entry = RuntimeAssetEntry(
            url="https://pyscript.net/releases/2026.3.1/core.js",
            sha256="abc123",
        )
        d = entry.to_dict()
        assert d["url"] == "https://pyscript.net/releases/2026.3.1/core.js"
        assert d["sha256"] == "abc123"

    def test_to_dict_with_null_sha256(self):
        entry = RuntimeAssetEntry(
            url="https://pyscript.net/releases/2026.3.1/core.js",
        )
        d = entry.to_dict()
        assert d["url"] == "https://pyscript.net/releases/2026.3.1/core.js"
        assert d["sha256"] is None

    def test_from_dict(self):
        data = {"url": "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.mjs", "sha256": "def456"}
        entry = RuntimeAssetEntry.from_dict(data)
        assert entry.url == "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.mjs"
        assert entry.sha256 == "def456"

    def test_from_dict_without_sha256(self):
        data = {"url": "https://pyscript.net/releases/2026.3.1/core.js"}
        entry = RuntimeAssetEntry.from_dict(data)
        assert entry.url == "https://pyscript.net/releases/2026.3.1/core.js"
        assert entry.sha256 is None


class TestLockfileRuntimeServing:
    def test_runtime_serving_cdn_default(self, tmp_path):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
        )
        path = tmp_path / "lock.json"
        save_lockfile(lockfile, path)
        loaded = load_lockfile(path)
        assert loaded is not None
        assert loaded.runtime_serving == "cdn"
        assert loaded.runtime_assets == {}

    def test_runtime_serving_local_roundtrip(self, tmp_path):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            runtime_serving="local",
            runtime_assets={
                "core.js": RuntimeAssetEntry(
                    url="https://pyscript.net/releases/2026.3.1/core.js",
                    sha256="abc123",
                ),
                "pyodide.mjs": RuntimeAssetEntry(
                    url="https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.mjs",
                    sha256="def456",
                ),
            },
        )
        path = tmp_path / "lock.json"
        save_lockfile(lockfile, path)
        loaded = load_lockfile(path)
        assert loaded is not None
        assert loaded.runtime_serving == "local"
        assert "core.js" in loaded.runtime_assets
        assert loaded.runtime_assets["core.js"].url == "https://pyscript.net/releases/2026.3.1/core.js"
        assert loaded.runtime_assets["core.js"].sha256 == "abc123"

    def test_runtime_assets_absent_in_cdn_mode_output(self, tmp_path):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            runtime_serving="cdn",
        )
        path = tmp_path / "lock.json"
        save_lockfile(lockfile, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "runtime_assets" not in data

    def test_runtime_assets_present_in_local_mode_output(self, tmp_path):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            runtime_serving="local",
            runtime_assets={
                "core.js": RuntimeAssetEntry(
                    url="https://pyscript.net/releases/2026.3.1/core.js",
                    sha256="abc123",
                ),
            },
        )
        path = tmp_path / "lock.json"
        save_lockfile(lockfile, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "runtime_assets" in data
        assert "core.js" in data["runtime_assets"]

    def test_backward_compat_standalone_assets(self, tmp_path):
        data = {
            "version": 2,
            "pyodide_version": "0.29.3",
            "pyscript_version": "2026.3.1",
            "wasm_serving": "cdn",
            "runtime_serving": "local",
            "wasm_packages": {},
            "pure_python_packages": {},
            "standalone_assets": {
                "core_js": {"url": "https://pyscript.net/releases/2026.3.1/core.js", "sha256": "abc123"},
            },
        }
        path = tmp_path / "lock.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        loaded = load_lockfile(path)
        assert loaded is not None
        assert loaded.runtime_serving == "local"
        assert "core_js" in loaded.runtime_assets


class TestGenerateLockfileRuntimeAssets:
    def test_runtime_local_populates_urls(self, tmp_path):

        from webcompy.cli._lockfile import generate_lockfile

        modules_dir = tmp_path / ".webcompy_modules"
        lockfile, _errors, _warnings = generate_lockfile(
            dependencies=[],
            pyscript_version="2026.3.1",
            modules_dir=modules_dir,
            runtime_serving="local",
        )
        assert lockfile.runtime_serving == "local"
        assert "core.js" in lockfile.runtime_assets
        assert "core.css" in lockfile.runtime_assets
        assert "pyodide.mjs" in lockfile.runtime_assets
        assert lockfile.runtime_assets["core.js"].url.startswith("https://pyscript.net/releases/")
        assert lockfile.runtime_assets["pyodide.mjs"].url.startswith("https://cdn.jsdelivr.net/pyodide/")
        assert lockfile.runtime_assets["core.js"].sha256 is None
        assert lockfile.runtime_assets["pyodide.mjs"].sha256 is None

    def test_runtime_cdn_no_runtime_assets(self, tmp_path):
        from webcompy.cli._lockfile import generate_lockfile

        modules_dir = tmp_path / ".webcompy_modules"
        lockfile, _errors, _warnings = generate_lockfile(
            dependencies=[],
            pyscript_version="2026.3.1",
            modules_dir=modules_dir,
            runtime_serving="cdn",
        )
        assert lockfile.runtime_serving == "cdn"
        assert lockfile.runtime_assets == {}
