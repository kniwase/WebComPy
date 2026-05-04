import hashlib
import zipfile

from webcompy.cli._wheel_builder import (
    _collect_package_files,
    _discover_packages,
    _normalize_name,
    _sha256_b64,
    _write_metadata,
    _write_record,
    _write_wheel,
    get_wheel_filename,
    make_bundled_wheel,
    make_webcompy_app_package,
    make_wheel,
)


class TestDiscoverPackages:
    def test_simple_package(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "hello.py").write_text("print('hello')")
        result = _discover_packages(pkg)
        assert result == ["myapp"]

    def test_nested_packages(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        sub = pkg / "sub"
        sub.mkdir()
        (sub / "__init__.py").write_text("")
        (sub / "mod.py").write_text("")
        result = _discover_packages(pkg)
        assert "myapp" in result
        assert "myapp.sub" in result

    def test_excludes_pycache(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        cache = pkg / "__pycache__"
        cache.mkdir()
        (cache / "mod.cpython-312.pyc").write_text("")
        result = _discover_packages(pkg)
        assert result == ["myapp"]

    def test_non_package_dirs_excluded(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        data = pkg / "data"
        data.mkdir()
        (data / "file.json").write_text("{}")
        result = _discover_packages(pkg)
        assert result == ["myapp"]

    def test_single_file_module(self, tmp_path):
        extracted = tmp_path / "six"
        extracted.mkdir()
        (extracted / "six.py").write_text("import six")
        result = _discover_packages(extracted)
        assert result == ["six"]

    def test_single_file_module_coexists_with_directory_packages(self, tmp_path):
        six_dir = tmp_path / "six"
        six_dir.mkdir()
        (six_dir / "six.py").write_text("")
        dateutil_dir = tmp_path / "dateutil"
        dateutil_dir.mkdir()
        (dateutil_dir / "__init__.py").write_text("")
        assert _discover_packages(six_dir) == ["six"]
        assert _discover_packages(dateutil_dir) == ["dateutil"]


class TestCollectPackageFiles:
    def test_py_files_collected(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "mod.py").write_text("x = 1")
        packages = ["myapp"]
        files = _collect_package_files(pkg, packages)
        arcs = {arc for _, arc in files}
        assert "myapp/__init__.py" in arcs
        assert "myapp/mod.py" in arcs

    def test_pyi_and_typed_collected(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "mod.pyi").write_text("")
        (pkg / "py.typed").write_text("")
        files = _collect_package_files(pkg, ["myapp"])
        arcs = {arc for _, arc in files}
        assert "myapp/mod.pyi" in arcs
        assert "myapp/py.typed" in arcs

    def test_package_data_glob(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        data_dir = pkg / "data"
        data_dir.mkdir()
        (data_dir / "cities.json").write_text("[]")
        (data_dir / "style.css").write_text("body{}")
        files = _collect_package_files(pkg, ["myapp"], {"myapp": ["data/*.json"]})
        arcs = {arc for _, arc in files}
        assert "myapp/data/cities.json" in arcs
        assert "myapp/data/style.css" not in arcs

    def test_no_package_data(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        files = _collect_package_files(pkg, ["myapp"])
        arcs = {arc for _, arc in files}
        assert "myapp/__init__.py" in arcs

    def test_single_file_module(self, tmp_path):
        extracted = tmp_path / "six"
        extracted.mkdir()
        (extracted / "six.py").write_text("import six")
        files = _collect_package_files(extracted, ["six"])
        arcs = {arc for _, arc in files}
        assert arcs == {"six.py"}


class TestSha256B64:
    def test_basic_hash(self):
        data = b"hello world"
        expected = "sha256=" + __import__("base64").urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(
            b"="
        ).decode("ascii")
        assert _sha256_b64(data) == expected

    def test_empty_data(self):
        result = _sha256_b64(b"")
        assert result.startswith("sha256=")
        assert len(result) > 7


class TestWriteMetadata:
    def test_metadata_content(self):
        result = _write_metadata("myapp", "1.0.0")
        assert "Metadata-Version: 2.4" in result
        assert "Name: myapp" in result
        assert "Version: 1.0.0" in result


class TestWriteWheel:
    def test_wheel_content(self):
        result = _write_wheel()
        assert "Wheel-Version: 1.0" in result
        assert "Generator: webcompy" in result
        assert "Root-Is-Purelib: true" in result
        assert "Tag: py3-none-any" in result


class TestWriteRecord:
    def test_record_content(self):
        entries = [
            ("myapp/__init__.py", "sha256=abc123=", 50),
            ("myapp/mod.py", "sha256=def456=", 100),
        ]
        result = _write_record(entries, "myapp-1.0.0.dist-info")
        assert "myapp/__init__.py,sha256=abc123=,50" in result
        assert "myapp/mod.py,sha256=def456=,100" in result
        assert "myapp-1.0.0.dist-info/RECORD,," in result


class TestNormalizeName:
    def test_simple(self):
        assert _normalize_name("myapp") == "myapp"

    def test_underscores(self):
        assert _normalize_name("my_app") == "my_app"

    def test_dots(self):
        assert _normalize_name("my.app") == "my_app"

    def test_mixed_case(self):
        assert _normalize_name("MyApp") == "myapp"


class TestGetWheelFilename:
    def test_simple_name(self):
        assert get_wheel_filename("myapp", "1.0.0") == "myapp-1.0.0-py3-none-any.whl"

    def test_underscore_name(self):
        assert get_wheel_filename("my_app", "1.0.0") == "my_app-1.0.0-py3-none-any.whl"

    def test_mixed_case_name(self):
        assert get_wheel_filename("MyApp", "2.3.4") == "myapp-2.3.4-py3-none-any.whl"

    def test_dotted_name(self):
        assert get_wheel_filename("my.app", "1.0.0") == "my_app-1.0.0-py3-none-any.whl"

    def test_matches_make_wheel_output(self, tmp_path):
        pkg = tmp_path / "test_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_wheel("test_pkg", pkg, dest, "1.2.3")
        assert result.name == get_wheel_filename("test_pkg", "1.2.3")

    def test_matches_make_bundled_wheel_output(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("")
        app_pkg = tmp_path / "my_app"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_bundled_wheel(
            "my_app",
            [("webcompy", webcompy_pkg), ("my_app", app_pkg)],
            dest,
            "1.0.0",
        )
        assert result.name == get_wheel_filename("my_app", "1.0.0")


class TestMakeWheel:
    def test_creates_wheel_file(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("# init")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_wheel("myapp", pkg, dest, "1.0.0")
        assert result.exists()
        assert result.name == "myapp-1.0.0-py3-none-any.whl"

    def test_wheel_is_valid_zip(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("# init")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_wheel("myapp", pkg, dest, "1.0.0")
        assert zipfile.is_zipfile(result)

    def test_wheel_contains_dist_info(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("# init")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_wheel("myapp", pkg, dest, "1.0.0")
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
            assert "myapp-1.0.0.dist-info/METADATA" in names
            assert "myapp-1.0.0.dist-info/WHEEL" in names
            assert "myapp-1.0.0.dist-info/RECORD" in names
            assert "myapp-1.0.0.dist-info/top_level.txt" in names

    def test_wheel_contains_source_files(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("# init")
        (pkg / "mod.py").write_text("x = 1")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_wheel("myapp", pkg, dest, "1.0.0")
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
            assert "myapp/__init__.py" in names
            assert "myapp/mod.py" in names

    def test_wheel_with_package_data(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("# init")
        data_dir = pkg / "data"
        data_dir.mkdir()
        (data_dir / "cities.json").write_text("[]")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_wheel("myapp", pkg, dest, "1.0.0", {"myapp": ["data/*.json"]})
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
            assert "myapp/data/cities.json" in names


class TestMakeBundledWheel:
    def test_creates_bundled_wheel(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("")
        app_pkg = tmp_path / "app"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_bundled_wheel(
            "app",
            [("webcompy", webcompy_pkg), ("app", app_pkg)],
            dest,
            "1.0.0",
        )
        assert result.exists()
        assert result.name == "app-1.0.0-py3-none-any.whl"

    def test_bundled_wheel_contains_both_packages(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("# wc")
        app_pkg = tmp_path / "app"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("# app")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_bundled_wheel(
            "app",
            [("webcompy", webcompy_pkg), ("app", app_pkg)],
            dest,
            "1.0.0",
        )
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
            assert "webcompy/__init__.py" in names
            assert "app/__init__.py" in names

    def test_bundled_wheel_top_level(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("")
        app_pkg = tmp_path / "app"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_bundled_wheel(
            "app",
            [("webcompy", webcompy_pkg), ("app", app_pkg)],
            dest,
            "1.0.0",
        )
        with zipfile.ZipFile(result) as zf:
            top_level = zf.read("app-1.0.0.dist-info/top_level.txt").decode()
            lines = top_level.strip().split("\n")
            assert "webcompy" in lines
            assert "app" in lines


class TestMakeWebcompyAppPackageBundledDeps:
    def test_bundled_deps_included(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("")
        app_pkg = tmp_path / "myapp"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        click_pkg = tmp_path / "click"
        click_pkg.mkdir()
        (click_pkg / "__init__.py").write_text("# click")
        (click_pkg / "core.py").write_text("# core")
        dest = tmp_path / "dist"
        dest.mkdir()

        result = make_webcompy_app_package(
            dest,
            webcompy_pkg,
            app_pkg,
            "1.0.0",
            bundled_deps=[("click", click_pkg)],
        )
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
            assert "click/__init__.py" in names
            assert "click/core.py" in names

    def test_bundled_deps_in_top_level(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("")
        app_pkg = tmp_path / "myapp"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        click_pkg = tmp_path / "click"
        click_pkg.mkdir()
        (click_pkg / "__init__.py").write_text("")
        dest = tmp_path / "dist"
        dest.mkdir()

        result = make_webcompy_app_package(
            dest,
            webcompy_pkg,
            app_pkg,
            "1.0.0",
            bundled_deps=[("click", click_pkg)],
        )
        with zipfile.ZipFile(result) as zf:
            dist_info = next(n for n in zf.namelist() if n.endswith("/top_level.txt"))
            top_level = zf.read(dist_info).decode()
            lines = top_level.strip().split("\n")
            assert "webcompy" in lines
            assert "myapp" in lines
            assert "click" in lines

    def test_no_bundled_deps(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("")
        app_pkg = tmp_path / "myapp"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        dest = tmp_path / "dist"
        dest.mkdir()

        result = make_webcompy_app_package(
            dest,
            webcompy_pkg,
            app_pkg,
            "1.0.0",
        )
        with zipfile.ZipFile(result) as zf:
            dist_info = next(n for n in zf.namelist() if n.endswith("/top_level.txt"))
            top_level = zf.read(dist_info).decode()
            lines = top_level.strip().split("\n")
            assert "webcompy" in lines
            assert "myapp" in lines

    def test_single_file_module_bundled_dep(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("")
        app_pkg = tmp_path / "myapp"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        six_dir = tmp_path / "six"
        six_dir.mkdir()
        (six_dir / "six.py").write_text("")
        dest = tmp_path / "dist"
        dest.mkdir()

        result = make_webcompy_app_package(
            dest,
            webcompy_pkg,
            app_pkg,
            "1.0.0",
            bundled_deps=[("six", six_dir)],
        )
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
            assert "six.py" in names
            dist_info = next(n for n in names if n.endswith("/top_level.txt"))
            top_level = zf.read(dist_info).decode()
            lines = top_level.strip().split("\n")
            assert "six" in lines
