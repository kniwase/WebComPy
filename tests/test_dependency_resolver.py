from __future__ import annotations

from webcompy.cli._dependency_resolver import (
    PackageKind,
    _classify_from_pyodide_lock,
    _find_package_dir,
    _is_pure_python_package,
    _resolve_transitive_deps_via_pyodide_lock,
    classify_dependencies,
)


class TestPackageKind:
    def test_enum_values(self):
        assert PackageKind.WASM.value == "wasm"
        assert PackageKind.CDN_PURE_PYTHON.value == "cdn_pure_python"
        assert PackageKind.LOCAL_PURE_PYTHON.value == "local_pure_python"

    def test_mutually_exclusive(self):
        kinds = {PackageKind.WASM, PackageKind.CDN_PURE_PYTHON, PackageKind.LOCAL_PURE_PYTHON}
        assert len(kinds) == 3


class TestClassifyFromPyodideLock:
    def test_wasm32_filename_classified_as_wasm(self):
        lock = {
            "packages": {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "package_type": "package",
                    "depends": [],
                    "sha256": "abc123",
                },
            }
        }
        assert _classify_from_pyodide_lock("numpy", lock) == PackageKind.WASM

    def test_pure_python_filename_classified_as_cdn(self):
        lock = {
            "packages": {
                "packaging": {
                    "version": "24.2",
                    "file_name": "packaging-24.2-py3-none-any.whl",
                    "package_type": "package",
                    "depends": [],
                    "sha256": "def456",
                },
            }
        }
        assert _classify_from_pyodide_lock("packaging", lock) == PackageKind.CDN_PURE_PYTHON

    def test_package_not_in_lock(self):
        lock = {"packages": {}}
        assert _classify_from_pyodide_lock("nonexistent", lock) is None

    def test_package_type_ignored_when_wasm32_in_filename(self):
        lock = {
            "packages": {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "package_type": "package",
                    "depends": [],
                    "sha256": "abc123",
                },
            }
        }
        assert _classify_from_pyodide_lock("numpy", lock) == PackageKind.WASM

    def test_no_package_type_field_uses_filename(self):
        lock = {
            "packages": {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "depends": [],
                    "sha256": "abc123",
                },
            }
        }
        assert _classify_from_pyodide_lock("numpy", lock) == PackageKind.WASM

    def test_shared_library_package_type_with_wasm32_filename(self):
        lock = {
            "packages": {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "package_type": "shared_library",
                    "depends": [],
                    "sha256": "abc123",
                },
            }
        }
        assert _classify_from_pyodide_lock("numpy", lock) == PackageKind.WASM


class TestIsPurePythonPackage:
    def test_pure_python_package(self, tmp_path):
        pkg_dir = tmp_path / "myapp"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "mod.py").write_text("x = 1")
        assert _is_pure_python_package(pkg_dir) is True

    def test_package_with_so_file(self, tmp_path):
        pkg_dir = tmp_path / "myapp"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "native.so").write_bytes(b"\x00")
        assert _is_pure_python_package(pkg_dir) is False

    def test_package_with_pyd_file(self, tmp_path):
        pkg_dir = tmp_path / "myapp"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "native.pyd").write_bytes(b"\x00")
        assert _is_pure_python_package(pkg_dir) is False

    def test_package_with_dylib_file(self, tmp_path):
        pkg_dir = tmp_path / "myapp"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "native.dylib").write_bytes(b"\x00")
        assert _is_pure_python_package(pkg_dir) is False

    def test_nested_so_file(self, tmp_path):
        pkg_dir = tmp_path / "myapp"
        pkg_dir.mkdir()
        sub = pkg_dir / "sub"
        sub.mkdir()
        (sub / "__init__.py").write_text("")
        (sub / "ext.so").write_bytes(b"\x00")
        assert _is_pure_python_package(pkg_dir) is False


class TestFindPackageDir:
    def test_find_installed_package(self):
        result = _find_package_dir("webcompy")
        assert result is not None
        assert result.is_dir()
        assert (result / "__init__.py").exists()

    def test_find_nonexistent_package(self):
        result = _find_package_dir("nonexistent_package_xyz_12345")
        assert result is None


class TestResolveTransitiveDepsViaPyodideLock:
    def test_direct_deps(self):
        lock = {
            "packages": {
                "numpy": {"version": "2.2.5", "depends": []},
                "httpx": {"version": "0.28.1", "depends": ["httpcore", "sniffio"]},
                "httpcore": {"version": "1.0.7", "depends": []},
                "sniffio": {"version": "1.3.1", "depends": []},
            }
        }
        result = _resolve_transitive_deps_via_pyodide_lock("httpx", lock)
        assert "httpcore" in result
        assert "sniffio" in result

    def test_nested_deps(self):
        lock = {
            "packages": {
                "a": {"version": "1.0", "depends": ["b"]},
                "b": {"version": "1.0", "depends": ["c"]},
                "c": {"version": "1.0", "depends": []},
            }
        }
        result = _resolve_transitive_deps_via_pyodide_lock("a", lock)
        assert "b" in result
        assert "c" in result

    def test_package_not_in_lock(self):
        lock = {"packages": {}}
        result = _resolve_transitive_deps_via_pyodide_lock("nonexistent", lock)
        assert len(result) == 0


class TestClassifyDependencies:
    def test_wasm_package_classified_correctly(self):
        lock = {
            "packages": {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "package_type": "package",
                    "depends": [],
                    "sha256": "abc123",
                },
            }
        }
        classified, errors, _warnings = classify_dependencies(["numpy"], lock)
        assert len(errors) == 0
        numpy_dep = next(d for d in classified if d.name == "numpy")
        assert numpy_dep.kind == PackageKind.WASM
        assert numpy_dep.source == "explicit"
        assert numpy_dep.kind != PackageKind.LOCAL_PURE_PYTHON
        assert numpy_dep.pyodide_file_name == "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl"
        assert numpy_dep.pyodide_sha256 == "abc123"

    def test_pure_python_in_pyodide_cdn(self):
        lock = {
            "packages": {
                "httpx": {
                    "version": "0.28.1",
                    "file_name": "httpx-0.28.1-py3-none-any.whl",
                    "depends": [],
                    "sha256": "def456",
                    "package_type": "package",
                },
            }
        }
        classified, _errors, _warnings = classify_dependencies(["httpx"], lock)
        httpx_dep = next(d for d in classified if d.name == "httpx")
        assert httpx_dep.kind == PackageKind.CDN_PURE_PYTHON
        assert httpx_dep.source == "explicit"
        assert httpx_dep.pyodide_file_name == "httpx-0.28.1-py3-none-any.whl"
        assert httpx_dep.pyodide_sha256 == "def456"

    def test_local_pure_python_classified_correctly(self):
        lock = {"packages": {}}
        classified, _errors, _warnings = classify_dependencies(["webcompy"], lock)
        wc_dep = next(d for d in classified if d.name == "webcompy")
        assert wc_dep.source == "explicit"
        assert wc_dep.kind == PackageKind.LOCAL_PURE_PYTHON
        assert wc_dep.pyodide_file_name is None
        assert wc_dep.pyodide_sha256 is None

    def test_missing_package_produces_error(self):
        lock = {"packages": {}}
        _classified, errors, _warnings = classify_dependencies(["nonexistent_package_xyz_12345"], lock)
        assert len(errors) > 0
        assert any("nonexistent_package_xyz_12345" in e for e in errors)

    def test_transitive_pure_python_in_pyodide_cdn(self):
        lock = {
            "packages": {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "package_type": "package",
                    "depends": ["packaging"],
                    "sha256": "abc123",
                },
                "packaging": {
                    "version": "24.2",
                    "file_name": "packaging-24.2-py3-none-any.whl",
                    "depends": [],
                    "sha256": "def456",
                },
            }
        }
        classified, errors, _warnings = classify_dependencies(["numpy"], lock)
        assert len(errors) == 0
        packaging_dep = next(d for d in classified if d.name == "packaging")
        assert packaging_dep.source == "transitive"
        assert packaging_dep.kind != PackageKind.LOCAL_PURE_PYTHON
        assert packaging_dep.pyodide_file_name == "packaging-24.2-py3-none-any.whl"

    def test_regression_numpy_with_package_type_package(self):
        lock = {
            "packages": {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "package_type": "package",
                    "depends": [],
                    "sha256": "abc123",
                },
            }
        }
        classified, errors, _warnings = classify_dependencies(["numpy"], lock)
        assert len(errors) == 0
        numpy_dep = next(d for d in classified if d.name == "numpy")
        assert numpy_dep.kind == PackageKind.WASM

    def test_wasm_detection_without_package_type(self):
        lock = {
            "packages": {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "depends": [],
                    "sha256": "abc123",
                },
            }
        }
        classified, errors, _warnings = classify_dependencies(["numpy"], lock)
        assert len(errors) == 0
        numpy_dep = next(d for d in classified if d.name == "numpy")
        assert numpy_dep.kind == PackageKind.WASM

    def test_cpython_module_detected_as_wasm(self):
        lock = {
            "packages": {
                "ssl": {
                    "version": "1.0",
                    "file_name": "ssl-1.0-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "package_type": "cpython_module",
                    "depends": [],
                    "sha256": "abc123",
                },
            }
        }
        classified, errors, _warnings = classify_dependencies(["ssl"], lock)
        assert len(errors) == 0
        ssl_dep = next(d for d in classified if d.name == "ssl")
        assert ssl_dep.kind == PackageKind.WASM

    def test_transitive_wasm_package(self):
        lock = {
            "packages": {
                "matplotlib": {
                    "version": "3.8.4",
                    "file_name": "matplotlib-3.8.4-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "package_type": "package",
                    "depends": ["numpy"],
                    "sha256": "mat123",
                },
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "package_type": "package",
                    "depends": [],
                    "sha256": "np123",
                },
            }
        }
        classified, errors, _warnings = classify_dependencies(["matplotlib"], lock)
        assert len(errors) == 0
        numpy_dep = next(d for d in classified if d.name == "numpy")
        assert numpy_dep.kind == PackageKind.WASM
        assert numpy_dep.source == "transitive"
