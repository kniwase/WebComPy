import hashlib
import zipfile

from webcompy.cli._wheel_builder import (
    _assets_to_package_data,
    _collect_package_files,
    _discover_packages,
    _filter_excluded_subpackages,
    _generate_assets_registry,
    _normalize_name,
    _sha256_b64,
    _write_metadata,
    _write_record,
    _write_wheel,
    get_stable_wheel_filename,
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
        data_dir = pkg / "data"
        data_dir.mkdir()
        (data_dir / "file.json").write_text("{}")
        files = _collect_package_files(pkg, ["myapp"])
        arcs = {arc for _, arc in files}
        assert "myapp/data/file.json" not in arcs


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

    def test_bundled_wheel_underscore_name(self, tmp_path):
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
            "2.0.0",
        )
        assert result.name == get_wheel_filename("my_app", "2.0.0")
        with zipfile.ZipFile(result) as zf:
            top_level = zf.read("my_app-2.0.0.dist-info/top_level.txt").decode()
            lines = top_level.strip().split("\n")
            assert "webcompy" in lines
            assert "my_app" in lines


class TestAssetsToPackageData:
    def test_simple_asset(self, tmp_path):
        app_pkg = tmp_path / "myapp"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        data_dir = app_pkg / "data"
        data_dir.mkdir()
        (data_dir / "cities.json").write_text("[]")
        result = _assets_to_package_data("myapp", {"logo": "data/cities.json"}, app_pkg)
        assert "myapp" in result
        assert any("cities.json" in p or "data/*" in p for p in result["myapp"])

    def test_root_level_asset(self, tmp_path):
        app_pkg = tmp_path / "myapp"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        (app_pkg / "icon.png").write_bytes(b"\x89PNG")
        result = _assets_to_package_data("myapp", {"icon": "icon.png"}, app_pkg)
        assert "myapp" in result
        assert any("icon.png" in p for p in result["myapp"])

    def test_multiple_assets_same_dir(self, tmp_path):
        app_pkg = tmp_path / "myapp"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        data_dir = app_pkg / "data"
        data_dir.mkdir()
        (data_dir / "a.json").write_text("{}")
        (data_dir / "b.json").write_text("{}")
        result = _assets_to_package_data("myapp", {"a": "data/a.json", "b": "data/b.json"}, app_pkg)
        assert "myapp" in result


class TestGenerateAssetsRegistry:
    def test_registry_content(self):
        result = _generate_assets_registry("myapp", {"logo": "logo.png", "config": "data/config.json"})
        assert '"logo"' in result
        assert '"myapp/logo.png"' in result
        assert '"config"' in result
        assert '"myapp/data/config.json"' in result
        assert "_REGISTRY" in result

    def test_empty_assets(self):
        result = _generate_assets_registry("myapp", {})
        assert "_REGISTRY: dict[str, str] = {}" in result


class TestMakeWebcompyAppPackageWithAssets:
    def test_bundled_wheel_with_assets(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("")
        app_pkg = tmp_path / "myapp"
        app_pkg.mkdir()
        (app_pkg / "__init__.py").write_text("")
        (app_pkg / "logo.png").write_bytes(b"\x89PNG")
        dest = tmp_path / "dist"
        dest.mkdir()
        result = make_webcompy_app_package(
            dest,
            webcompy_pkg,
            app_pkg,
            "1.0.0",
            assets={"logo": "logo.png"},
        )
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
            assert "myapp/logo.png" in names
            assert "myapp/_assets_registry.py" in names
            registry = zf.read("myapp/_assets_registry.py").decode()
            assert '"logo"' in registry
            assert '"myapp/logo.png"' in registry

    def test_bundled_wheel_without_assets(self, tmp_path):
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
            names = zf.namelist()
            assert "myapp/_assets_registry.py" not in names


class TestFilterExcludedSubpackages:
    def test_excludes_specified_subpackages(self):
        packages = ["webcompy", "webcompy.cli", "webcompy.cli._server", "webcompy.app", "webcompy.elements"]
        result = _filter_excluded_subpackages(packages, "webcompy", {"cli"})
        assert "webcompy" in result
        assert "webcompy.cli" not in result
        assert "webcompy.cli._server" not in result
        assert "webcompy.app" in result
        assert "webcompy.elements" in result

    def test_no_exclude_returns_all(self):
        packages = ["webcompy", "webcompy.cli", "webcompy.app"]
        result = _filter_excluded_subpackages(packages, "webcompy", set())
        assert result == packages

    def test_different_top_level(self):
        packages = ["myapp", "myapp.cli", "myapp.views"]
        result = _filter_excluded_subpackages(packages, "myapp", {"cli"})
        assert "myapp" in result
        assert "myapp.cli" not in result
        assert "myapp.views" in result


class TestGetStableWheelFilename:
    def test_simple_name(self):
        assert get_stable_wheel_filename("myapp") == "myapp-0-py3-none-any.whl"

    def test_underscore_name(self):
        assert get_stable_wheel_filename("my_app") == "my_app-0-py3-none-any.whl"

    def test_mixed_case_name(self):
        assert get_stable_wheel_filename("MyApp") == "myapp-0-py3-none-any.whl"

    def test_no_version_in_filename(self):
        result = get_stable_wheel_filename("myapp")
        assert "-1.0.0-" not in result
        assert result == "myapp-0-py3-none-any.whl"


class TestMakeWebcompyAppPackageExcludesCli:
    def test_excludes_cli_directory(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("")
        cli_dir = webcompy_pkg / "cli"
        cli_dir.mkdir()
        (cli_dir / "__init__.py").write_text("")
        (cli_dir / "_server.py").write_text("# server")
        app_dir = webcompy_pkg / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")
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
            names = zf.namelist()
            assert "webcompy/__init__.py" in names
            assert "webcompy/app/__init__.py" in names
            cli_files = [n for n in names if n.startswith("webcompy/cli/")]
            assert len(cli_files) == 0
            assert "webcompy/cli/__init__.py" not in names
            assert "webcompy/cli/_server.py" not in names

    def test_stable_filename(self, tmp_path):
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
        assert result.name == "myapp-0-py3-none-any.whl"

    def test_top_level_excludes_cli(self, tmp_path):
        webcompy_pkg = tmp_path / "webcompy"
        webcompy_pkg.mkdir()
        (webcompy_pkg / "__init__.py").write_text("")
        cli_dir = webcompy_pkg / "cli"
        cli_dir.mkdir()
        (cli_dir / "__init__.py").write_text("")
        app_dir = webcompy_pkg / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")
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
