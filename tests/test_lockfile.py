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
    validate_local_environment,
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

    def test_pyodide_packages_pure_python_not_included_in_bundled_deps(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "cycler": PyodidePackageEntry(
                    version="0.12.1", file_name="cycler-0.12.1-py3-none-any.whl", is_wasm=False
                ),
            },
            bundled_packages={
                "webcompy": BundledPackageEntry(version="0.1.0", source="explicit", is_pure_python=True),
            },
        )
        result = get_bundled_deps(lockfile)
        names = [name for name, _ in result]
        assert "webcompy" in names
        assert "cycler" not in names

    def test_none_lockfile_returns_empty(self):
        result = get_bundled_deps(None)
        assert result == []


class TestGetPyodidePackageNames:
    def test_returns_wasm_names_only(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "numpy": PyodidePackageEntry(version="2.2.5", file_name="numpy.whl", is_wasm=True, source="explicit"),
                "httpx": PyodidePackageEntry(version="0.28.1", file_name="httpx.whl", is_wasm=False, source="explicit"),
            },
            bundled_packages={
                "flask": BundledPackageEntry(version="3.1.0", source="explicit", is_pure_python=True),
            },
        )
        result = get_pyodide_package_names(lockfile)
        assert "numpy" in result
        assert "httpx" not in result
        assert "flask" not in result

    def test_none_lockfile_returns_empty(self):
        result = get_pyodide_package_names(None)
        assert result == []


class TestValidateLocalEnvironment:
    def test_matching_versions_no_errors(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={},
            bundled_packages={
                "webcompy": BundledPackageEntry(
                    version=_get_actual_version("webcompy"),
                    source="explicit",
                    is_pure_python=True,
                ),
            },
        )
        errors, warnings = validate_local_environment(lockfile)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_missing_package_produces_error(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={},
            bundled_packages={
                "nonexistent_package_xyz_12345": BundledPackageEntry(
                    version="1.0.0",
                    source="explicit",
                    is_pure_python=True,
                ),
            },
        )
        errors, _warnings = validate_local_environment(lockfile)
        assert len(errors) == 1
        assert "nonexistent_package_xyz_12345" in errors[0]
        assert "1.0.0" in errors[0]
        assert "pip install" in errors[0]

    def test_version_mismatch_produces_error(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={},
            bundled_packages={
                "webcompy": BundledPackageEntry(
                    version="0.0.0-fake",
                    source="explicit",
                    is_pure_python=True,
                ),
            },
        )
        errors, _warnings = validate_local_environment(lockfile)
        assert len(errors) == 1
        assert "version mismatch" in errors[0]
        assert "0.0.0-fake" in errors[0]
        assert "pip install" in errors[0]

    def test_wasm_pyodide_package_skipped(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "numpy": PyodidePackageEntry(
                    version="99.99.99",
                    file_name="numpy-wasm32.whl",
                    is_wasm=True,
                ),
            },
            bundled_packages={},
        )
        errors, warnings = validate_local_environment(lockfile)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_non_wasm_pyodide_package_version_mismatch_produces_warning(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={
                "webcompy": PyodidePackageEntry(
                    version="0.0.0-fake",
                    file_name="webcompy-py3-none-any.whl",
                    is_wasm=False,
                ),
            },
            bundled_packages={},
        )
        errors, warnings = validate_local_environment(lockfile)
        assert len(errors) == 0
        assert len(warnings) == 1
        assert "version mismatch" in warnings[0]

    def test_non_pure_python_bundled_package_skipped_for_version_check(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={},
            bundled_packages={
                "some_c_ext": BundledPackageEntry(
                    version="1.0.0",
                    source="explicit",
                    is_pure_python=False,
                ),
            },
        )
        errors, warnings = validate_local_environment(lockfile)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_multiple_issues_reported(self):
        lockfile = Lockfile(
            pyodide_version="0.29.3",
            pyscript_version="2026.3.1",
            pyodide_packages={},
            bundled_packages={
                "nonexistent_xyz": BundledPackageEntry(
                    version="1.0.0",
                    source="explicit",
                    is_pure_python=True,
                ),
                "webcompy": BundledPackageEntry(
                    version="0.0.0-fake",
                    source="explicit",
                    is_pure_python=True,
                ),
            },
        )
        errors, _warnings = validate_local_environment(lockfile)
        assert len(errors) == 2


class TestGenerateLockfile:
    def _mock_pyodide_lock(self, packages=None):
        lock = {"packages": packages or {}}
        return lock

    def test_wasm_package_routed_to_pyodide_packages(self, monkeypatch, tmp_path):
        from webcompy.cli._lockfile import generate_lockfile

        lock = self._mock_pyodide_lock(
            {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "depends": [],
                },
            }
        )
        monkeypatch.setattr("webcompy.cli._lockfile.fetch_pyodide_lock", lambda v: lock)
        monkeypatch.setattr("webcompy.cli._lockfile.get_pyodide_version", lambda v: "0.29.3")

        lockfile, errors, _warnings = generate_lockfile(["numpy"], "2026.3.1")

        assert len(errors) == 0
        assert "numpy" in lockfile.pyodide_packages
        assert lockfile.pyodide_packages["numpy"].is_wasm is True
        assert "numpy" not in lockfile.bundled_packages

    def test_pure_python_pyodide_cdn_routed_to_pyodide_packages(self, monkeypatch, tmp_path):
        from webcompy.cli._lockfile import generate_lockfile

        lock = self._mock_pyodide_lock(
            {
                "httpx": {
                    "version": "0.28.1",
                    "file_name": "httpx-0.28.1-py3-none-any.whl",
                    "depends": [],
                },
            }
        )
        monkeypatch.setattr("webcompy.cli._lockfile.fetch_pyodide_lock", lambda v: lock)
        monkeypatch.setattr("webcompy.cli._lockfile.get_pyodide_version", lambda v: "0.29.3")

        lockfile, errors, _warnings = generate_lockfile(["httpx"], "2026.3.1")

        assert len(errors) == 0
        assert "httpx" in lockfile.pyodide_packages
        assert lockfile.pyodide_packages["httpx"].is_wasm is False
        assert "httpx" not in lockfile.bundled_packages

    def test_local_pure_python_routed_to_bundled_packages(self, monkeypatch, tmp_path):
        from webcompy.cli._lockfile import generate_lockfile

        lock = self._mock_pyodide_lock({})
        monkeypatch.setattr("webcompy.cli._lockfile.fetch_pyodide_lock", lambda v: lock)
        monkeypatch.setattr("webcompy.cli._lockfile.get_pyodide_version", lambda v: "0.29.3")

        lockfile, errors, _warnings = generate_lockfile(["webcompy"], "2026.3.1")

        assert len(errors) == 0
        assert "webcompy" in lockfile.bundled_packages
        assert lockfile.bundled_packages["webcompy"].source == "explicit"
        assert lockfile.bundled_packages["webcompy"].is_pure_python is True
        assert "webcompy" not in lockfile.pyodide_packages

    def test_transitive_wasm_routed_to_pyodide_packages(self, monkeypatch, tmp_path):
        from webcompy.cli._lockfile import generate_lockfile

        lock = self._mock_pyodide_lock(
            {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "depends": [],
                },
                "scipy": {
                    "version": "1.14.1",
                    "file_name": "scipy-1.14.1-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "depends": ["numpy"],
                },
            }
        )
        monkeypatch.setattr("webcompy.cli._lockfile.fetch_pyodide_lock", lambda v: lock)
        monkeypatch.setattr("webcompy.cli._lockfile.get_pyodide_version", lambda v: "0.29.3")

        lockfile, errors, _warnings = generate_lockfile(["scipy"], "2026.3.1")

        assert len(errors) == 0
        assert "scipy" in lockfile.pyodide_packages
        assert lockfile.pyodide_packages["scipy"].source == "explicit"
        assert "numpy" in lockfile.pyodide_packages
        assert lockfile.pyodide_packages["numpy"].source == "transitive"

    def test_transitive_pure_python_pyodide_cdn_routed_to_pyodide_packages(self, monkeypatch, tmp_path):
        from webcompy.cli._lockfile import generate_lockfile

        lock = self._mock_pyodide_lock(
            {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "depends": ["packaging"],
                },
                "packaging": {
                    "version": "24.2",
                    "file_name": "packaging-24.2-py3-none-any.whl",
                    "depends": [],
                },
            }
        )
        monkeypatch.setattr("webcompy.cli._lockfile.fetch_pyodide_lock", lambda v: lock)
        monkeypatch.setattr("webcompy.cli._lockfile.get_pyodide_version", lambda v: "0.29.3")

        lockfile, errors, _warnings = generate_lockfile(["numpy"], "2026.3.1")

        assert len(errors) == 0
        assert "packaging" in lockfile.pyodide_packages
        assert lockfile.pyodide_packages["packaging"].is_wasm is False
        assert lockfile.pyodide_packages["packaging"].source == "transitive"
        assert "packaging" not in lockfile.bundled_packages

    def test_mixed_dependencies_routing(self, monkeypatch, tmp_path):
        from webcompy.cli._lockfile import generate_lockfile

        lock = self._mock_pyodide_lock(
            {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "depends": [],
                },
                "httpx": {
                    "version": "0.28.1",
                    "file_name": "httpx-0.28.1-py3-none-any.whl",
                    "depends": [],
                },
            }
        )
        monkeypatch.setattr("webcompy.cli._lockfile.fetch_pyodide_lock", lambda v: lock)
        monkeypatch.setattr("webcompy.cli._lockfile.get_pyodide_version", lambda v: "0.29.3")

        lockfile, errors, _warnings = generate_lockfile(["numpy", "httpx", "webcompy"], "2026.3.1")

        assert len(errors) == 0
        assert "numpy" in lockfile.pyodide_packages
        assert lockfile.pyodide_packages["numpy"].is_wasm is True
        assert "httpx" in lockfile.pyodide_packages
        assert lockfile.pyodide_packages["httpx"].is_wasm is False
        assert "webcompy" in lockfile.bundled_packages
        assert lockfile.bundled_packages["webcompy"].source == "explicit"
        assert "webcompy" not in lockfile.pyodide_packages


def _get_actual_version(package_name: str) -> str:
    from webcompy.cli._dependency_resolver import _get_package_version

    v = _get_package_version(package_name)
    return v or "0.0.0"
