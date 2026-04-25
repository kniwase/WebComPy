from __future__ import annotations

from webcompy.cli._dependency_resolver import (
    _find_package_dir,
    _is_pure_python_package,
    _resolve_transitive_deps_via_pyodide_lock,
    classify_dependencies,
)


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
                "numpy": {
                    "version": "2.2.5",
                    "depends": [],
                },
                "httpx": {
                    "version": "0.28.1",
                    "depends": ["httpcore", "sniffio"],
                },
                "httpcore": {
                    "version": "1.0.7",
                    "depends": [],
                },
                "sniffio": {
                    "version": "1.3.1",
                    "depends": [],
                },
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
    def test_wasm_package_classified_as_cdn(self):
        lock = {
            "packages": {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "depends": [],
                },
            }
        }
        classified, errors = classify_dependencies(["numpy"], lock)
        assert len(errors) == 0
        numpy_dep = next(d for d in classified if d.name == "numpy")
        assert numpy_dep.is_wasm is True
        assert numpy_dep.source == "pyodide_cdn"
        assert numpy_dep.is_pure_python is False

    def test_pure_python_in_pyodide_lock_classified_for_bundling(self):
        lock = {
            "packages": {
                "httpx": {
                    "version": "0.28.1",
                    "file_name": "httpx-0.28.1-py3-none-any.whl",
                    "depends": [],
                },
            }
        }
        classified, _errors = classify_dependencies(["httpx"], lock)
        httpx_dep = next(d for d in classified if d.name == "httpx")
        assert httpx_dep.is_wasm is False
        assert httpx_dep.source == "pyodide_cdn"
        assert httpx_dep.is_pure_python is True

    def test_local_pure_python_classified_as_bundled(self):
        lock = {"packages": {}}
        classified, _errors = classify_dependencies(["webcompy"], lock)
        wc_dep = next(d for d in classified if d.name == "webcompy")
        assert wc_dep.source == "explicit"
        assert wc_dep.is_pure_python is True
        assert wc_dep.is_wasm is False

    def test_missing_package_produces_error(self):
        lock = {"packages": {}}
        _classified, errors = classify_dependencies(["nonexistent_package_xyz_12345"], lock)
        assert len(errors) > 0
        assert any("nonexistent_package_xyz_12345" in e for e in errors)

    def test_none_lock_uses_local_fallback(self):
        classified, _errors = classify_dependencies(["webcompy"], None)
        wc_dep = next(d for d in classified if d.name == "webcompy")
        assert wc_dep.source == "explicit"
        assert wc_dep.is_pure_python is True

    def test_wasm_transitive_deps_resolved(self):
        lock = {
            "packages": {
                "numpy": {
                    "version": "2.2.5",
                    "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
                    "depends": [],
                },
            }
        }
        classified, errors = classify_dependencies(["numpy"], lock)
        assert len(errors) == 0
        numpy_dep = next(d for d in classified if d.name == "numpy")
        assert numpy_dep.is_wasm is True
