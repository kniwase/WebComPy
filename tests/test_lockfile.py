import json

from webcompy.cli._lockfile import (
    LOCKFILE_VERSION,
    BundledPackageEntry,
    Lockfile,
    PyodidePackageEntry,
    get_bundled_deps,
    get_pyodide_package_names,
    load_lockfile,
    save_lockfile,
    validate_lockfile,
)


class TestPyodidePackageEntry:
    def test_to_dict(self):
        entry = PyodidePackageEntry(
            version="2.2.5",
            file_name="numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
            is_wasm=True,
            source="explicit",
        )
        d = entry.to_dict()
        assert d["version"] == "2.2.5"
        assert d["is_wasm"] is True
        assert d["source"] == "explicit"

    def test_from_dict(self):
        data = {"version": "2.2.5", "file_name": "numpy.whl", "is_wasm": True, "source": "explicit"}
        entry = PyodidePackageEntry.from_dict(data)
        assert entry.version == "2.2.5"
        assert entry.is_wasm is True
        assert entry.source == "explicit"

    def test_from_dict_implicit_source(self):
        data = {"version": "2.2.5", "file_name": "numpy.whl", "is_wasm": True}
        entry = PyodidePackageEntry.from_dict(data)
        assert entry.source == "explicit"


class TestBundledPackageEntry:
    def test_to_dict(self):
        entry = BundledPackageEntry(version="3.1.0", source="explicit", is_pure_python=True)
        d = entry.to_dict()
        assert d["version"] == "3.1.0"
        assert d["source"] == "explicit"

    def test_from_dict(self):
        data = {"version": "3.1.0", "source": "transitive", "is_pure_python": True}
        entry = BundledPackageEntry.from_dict(data)
        assert entry.version == "3.1.0"
        assert entry.source == "transitive"


class TestLockfile:
    def test_to_dict(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "numpy": PyodidePackageEntry(version="2.2.5", file_name="numpy.whl", is_wasm=True),
            },
            bundled_packages={
                "flask": BundledPackageEntry(version="3.1.0", source="explicit", is_pure_python=True),
            },
        )
        d = lockfile.to_dict()
        assert d["version"] == LOCKFILE_VERSION
        assert d["pyodide_version"] == "0.29.3"
        assert "numpy" in d["pyodide_packages"]
        assert "flask" in d["bundled_packages"]
        assert "standalone_assets" in d


class TestSaveLoadLockfile:
    def test_roundtrip(self, tmp_path):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "numpy": PyodidePackageEntry(version="2.2.5", file_name="numpy.whl", is_wasm=True),
            },
            bundled_packages={
                "flask": BundledPackageEntry(version="3.1.0", source="explicit", is_pure_python=True),
            },
        )
        path = tmp_path / "webcompy-lock.json"
        save_lockfile(lockfile, path)
        loaded = load_lockfile(path)
        assert loaded is not None
        assert loaded.pyodide_version == "0.29.3"
        assert "numpy" in loaded.pyodide_packages
        assert loaded.pyodide_packages["numpy"].is_wasm is True
        assert "flask" in loaded.bundled_packages
        assert loaded.bundled_packages["flask"].source == "explicit"

    def test_load_nonexistent_returns_none(self, tmp_path):
        result = load_lockfile(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_invalid_json_returns_none(self, tmp_path):
        path = tmp_path / "webcompy-lock.json"
        path.write_text("not json", encoding="utf-8")
        result = load_lockfile(path)
        assert result is None

    def test_load_wrong_version_returns_none(self, tmp_path):
        path = tmp_path / "webcompy-lock.json"
        path.write_text(
            json.dumps({"version": 999, "pyodide_version": "0.29.3", "pyscript_version": "2026.3.1"}), encoding="utf-8"
        )
        result = load_lockfile(path)
        assert result is None


class TestValidateLockfile:
    def test_valid_lockfile(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "numpy": PyodidePackageEntry(version="2.2.5", file_name="numpy.whl", is_wasm=True),
            },
            bundled_packages={
                "flask": BundledPackageEntry(version="3.1.0", source="explicit", is_pure_python=True),
            },
        )
        issues = validate_lockfile(lockfile, ["numpy", "flask"])
        assert len(issues) == 0

    def test_missing_dependency(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={},
            bundled_packages={
                "flask": BundledPackageEntry(version="3.1.0", source="explicit", is_pure_python=True),
            },
        )
        issues = validate_lockfile(lockfile, ["flask", "requests"])
        assert len(issues) > 0

    def test_transitive_pyodide_packages_not_flagged_as_extra(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "numpy": PyodidePackageEntry(version="2.2.5", file_name="numpy.whl", is_wasm=True, source="explicit"),
                "scipy": PyodidePackageEntry(
                    version="1.14.1", file_name="scipy.whl", is_wasm=True, source="transitive"
                ),
            },
            bundled_packages={},
        )
        issues = validate_lockfile(lockfile, ["numpy"])
        assert len(issues) == 0


class TestGetBundledDeps:
    def test_returns_pure_python_bundled_packages(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "numpy": PyodidePackageEntry(version="2.2.5", file_name="numpy.whl", is_wasm=True),
            },
            bundled_packages={
                "webcompy": BundledPackageEntry(version="0.1.0", source="explicit", is_pure_python=True),
            },
        )
        result = get_bundled_deps(lockfile)
        names = [name for name, _ in result]
        assert "webcompy" in names
        assert "numpy" not in names

    def test_includes_pure_python_pyodide_packages(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "httpx": PyodidePackageEntry(
                    version="0.28.1", file_name="httpx-0.28.1-py3-none-any.whl", is_wasm=False
                ),
            },
            bundled_packages={},
        )
        result = get_bundled_deps(lockfile)
        names = [name for name, _ in result]
        assert "httpx" in names

    def test_none_lockfile_returns_empty(self):
        result = get_bundled_deps(None)
        assert result == []


class TestGetPyodidePackageNames:
    def test_returns_wasm_and_fallback_cdn_names_only(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "numpy": PyodidePackageEntry(version="2.2.5", file_name="numpy.whl", is_wasm=True, source="explicit"),
                "httpx": PyodidePackageEntry(version="0.28.1", file_name="httpx.whl", is_wasm=False, source="explicit"),
            },
            bundled_packages={
                "flask": BundledPackageEntry(version="3.1.0", source="explicit", is_pure_python=True),
                "missing_pkg": BundledPackageEntry(version="0.0.0", source="fallback_cdn", is_pure_python=True),
            },
        )
        result = get_pyodide_package_names(lockfile)
        assert "numpy" in result
        assert "httpx" not in result
        assert "flask" not in result
        assert "missing_pkg" in result

    def test_none_lockfile_returns_empty(self):
        result = get_pyodide_package_names(None)
        assert result == []
