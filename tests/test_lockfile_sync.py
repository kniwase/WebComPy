import types
from unittest.mock import patch

import pytest

from webcompy.app._config import AppConfig, LockfileSyncConfig
from webcompy.cli._exception import WebComPyCliException
from webcompy.cli._lockfile import Lockfile, PurePythonPackageEntry, WasmPackageEntry
from webcompy.cli._lockfile_sync import (
    discover_project_root,
    discover_requirements_path,
    export_requirements,
    install_requirements,
    record_requirements_path,
    resolve_dependencies,
    sync,
    sync_from_pyproject_toml,
    sync_from_requirements_txt,
)
from webcompy.cli._utils import get_lockfile_sync_config


class TestDiscoverProjectRoot:
    def test_pyproject_in_parent(self, tmp_path):
        parent = tmp_path / "project"
        parent.mkdir()
        (parent / "pyproject.toml").write_text("[project]\nname='test'\n")
        app_dir = parent / "my_app"
        app_dir.mkdir()
        result = discover_project_root(app_dir)
        assert result == parent

    def test_pyproject_in_grandparent(self, tmp_path):
        grandparent = tmp_path / "workspace" / "project"
        grandparent.mkdir(parents=True)
        (grandparent / "pyproject.toml").write_text("[project]\nname='test'\n")
        app_dir = grandparent / "pkg" / "my_app"
        app_dir.mkdir(parents=True)
        result = discover_project_root(app_dir)
        assert result == grandparent

    def test_pyproject_in_app_dir_itself(self, tmp_path):
        app_dir = tmp_path / "my_app"
        app_dir.mkdir()
        (app_dir / "pyproject.toml").write_text("[project]\nname='test'\n")
        result = discover_project_root(app_dir)
        assert result == app_dir

    def test_no_pyproject_raises(self, tmp_path):
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        with pytest.raises(WebComPyCliException, match=r"pyproject\.toml"):
            discover_project_root(app_dir)

    def test_nearest_pyproject_wins(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        (root / "pyproject.toml").write_text("[project]\nname='root'\n")
        sub = root / "sub"
        sub.mkdir()
        (sub / "pyproject.toml").write_text("[project]\nname='sub'\n")
        result = discover_project_root(sub)
        assert result == sub


class TestDiscoverRequirementsPath:
    def test_explicit_relative_path(self, tmp_path):
        app_dir = tmp_path / "project" / "my_app"
        app_dir.mkdir(parents=True)
        (tmp_path / "project" / "pyproject.toml").write_text("[project]\n")
        config = LockfileSyncConfig(requirements_path="../requirements.txt")
        result = discover_requirements_path(app_dir, config)
        assert result == (app_dir / "../requirements.txt").resolve()

    def test_explicit_absolute_path(self, tmp_path):
        app_dir = tmp_path / "project" / "my_app"
        app_dir.mkdir(parents=True)
        abs_path = tmp_path / "custom_requirements.txt"
        config = LockfileSyncConfig(requirements_path=str(abs_path))
        result = discover_requirements_path(app_dir, config)
        assert result == abs_path

    def test_auto_discovery(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir()
        (root / "pyproject.toml").write_text("[project]\n")
        app_dir = root / "my_app"
        app_dir.mkdir()
        result = discover_requirements_path(app_dir, LockfileSyncConfig())
        assert result == root / "requirements.txt"

    def test_auto_discovery_default_config(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir()
        (root / "pyproject.toml").write_text("[project]\n")
        app_dir = root / "my_app"
        app_dir.mkdir()
        result = discover_requirements_path(app_dir, None)
        assert result == root / "requirements.txt"


class TestGetLockfileSyncConfig:
    def test_config_with_sync_group(self):
        from webcompy.app._config import LockfileSyncConfig as LSC

        mock_module = types.SimpleNamespace(lockfile_sync_config=LSC(sync_group="browser"))

        def mock_import(name):
            if name == "webcompy_server_config":
                return mock_module
            raise ModuleNotFoundError

        with patch("webcompy.cli._utils.import_module", side_effect=mock_import):
            config = get_lockfile_sync_config()
        assert config.sync_group == "browser"
        assert config.requirements_path is None

    def test_config_without_lockfile_sync_config(self):
        mock_module = types.SimpleNamespace()

        def mock_import(name):
            if name == "webcompy_server_config":
                return mock_module
            raise ModuleNotFoundError

        with patch("webcompy.cli._utils.import_module", side_effect=mock_import):
            config = get_lockfile_sync_config()
        assert config.requirements_path is None
        assert config.sync_group is None

    def test_missing_config_file(self):
        with patch("webcompy.cli._utils.import_module", side_effect=ModuleNotFoundError):
            config = get_lockfile_sync_config()
        assert config.requirements_path is None
        assert config.sync_group is None


def _make_lockfile():
    return Lockfile(
        pyodide_version="0.24.0",
        pyscript_version="2024.1.1",
        wasm_packages={
            "numpy": WasmPackageEntry(
                version="2.2.5", file_name="numpy-2.2.5-cp312-cp312/emscripten_3_1_58_wasm32.whl"
            ),
        },
        pure_python_packages={
            "jinja2": PurePythonPackageEntry(
                version="3.1.6",
                source="explicit",
                in_pyodide_cdn=True,
                pyodide_file_name="Jinja2-3.1.6-cp312-cp312-emscripten_3_1_58_wasm32.whl",
                pyodide_sha256="abc",
            ),
            "markupsafe": PurePythonPackageEntry(version="2.1.5", source="explicit", in_pyodide_cdn=False),
            "click": PurePythonPackageEntry(version="8.1.7", source="explicit", in_pyodide_cdn=False),
        },
    )


class TestExportRequirements:
    def test_all_packages(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "requirements.txt"
        export_requirements(lockfile, path)
        content = path.read_text(encoding="utf-8")
        assert "markupsafe==2.1.5" in content
        assert "click==8.1.7" in content
        assert "jinja2==3.1.6" in content
        assert "numpy==2.2.5" in content

    def test_sorted_alphabetically(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "requirements.txt"
        export_requirements(lockfile, path)
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        entries = [line for line in lines if not line.startswith("#") and line]
        assert entries == sorted(entries, key=str.lower)

    def test_header_comment(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "requirements.txt"
        export_requirements(lockfile, path)
        lines = path.read_text(encoding="utf-8").split("\n")
        assert lines[0] == "# Generated by webcompy lock --export"
        assert lines[1] == ""

    def test_empty_lockfile(self, tmp_path):
        lockfile = Lockfile(pyodide_version="0.24.0", pyscript_version="2024.1.1")
        path = tmp_path / "requirements.txt"
        export_requirements(lockfile, path)
        content = path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert lines[0] == "# Generated by webcompy lock --export"

    def test_creates_parent_dirs(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "sub" / "dir" / "requirements.txt"
        export_requirements(lockfile, path)
        assert path.exists()


class TestRecordRequirementsPath:
    def test_adds_config_to_file(self, tmp_path):
        app_dir = tmp_path / "project" / "my_app"
        app_dir.mkdir(parents=True)
        (tmp_path / "project" / "pyproject.toml").write_text("[project]\n")
        config_path = app_dir / "webcompy_server_config.py"
        config_path.write_text(
            "from webcompy.app._config import GenerateConfig, ServerConfig\n\n"
            "server_config = ServerConfig(port=8080, dev=False)\n"
            "generate_config = GenerateConfig(dist='docs')\n",
            encoding="utf-8",
        )
        record_requirements_path(app_dir, tmp_path / "project" / "requirements.txt", config_path)
        content = config_path.read_text(encoding="utf-8")
        assert "LockfileSyncConfig" in content

    def test_existing_config_no_change(self, tmp_path, capsys):
        app_dir = tmp_path / "project" / "my_app"
        app_dir.mkdir(parents=True)
        (tmp_path / "project" / "pyproject.toml").write_text("[project]\n")
        config_path = app_dir / "webcompy_server_config.py"
        original = (
            "from webcompy.app._config import GenerateConfig, LockfileSyncConfig, ServerConfig\n\n"
            "server_config = ServerConfig(port=8080, dev=False)\n"
            "generate_config = GenerateConfig(dist='docs')\n"
            "lockfile_sync_config = LockfileSyncConfig(sync_group='browser')\n"
        )
        config_path.write_text(original, encoding="utf-8")
        record_requirements_path(app_dir, tmp_path / "project" / "requirements.txt", config_path)
        content = config_path.read_text(encoding="utf-8")
        assert content == original


class TestSyncFromRequirementsTxt:
    def test_matching_versions(self, tmp_path):
        lockfile = _make_lockfile()
        req_path = tmp_path / "requirements.txt"
        req_path.write_text(
            "markupsafe==2.1.5\nclick==8.1.7\njinja2==3.1.6\n",
            encoding="utf-8",
        )
        lines = sync_from_requirements_txt(lockfile, req_path)
        assert "✓ markupsafe: 2.1.5 (matches)" in lines
        assert "✓ click: 8.1.7 (matches)" in lines
        assert "✓ jinja2: 3.1.6 (matches)" in lines

    def test_version_mismatch(self, tmp_path):
        lockfile = _make_lockfile()
        req_path = tmp_path / "requirements.txt"
        req_path.write_text("markupsafe==3.0.2\n", encoding="utf-8")
        lines = sync_from_requirements_txt(lockfile, req_path)
        mismatch_lines = [line for line in lines if "mismatch" in line]
        assert len(mismatch_lines) == 1
        assert "markupsafe" in mismatch_lines[0]

    def test_extra_entry(self, tmp_path):
        lockfile = _make_lockfile()
        req_path = tmp_path / "requirements.txt"
        req_path.write_text("some-tool==1.0.0\n", encoding="utf-8")
        lines = sync_from_requirements_txt(lockfile, req_path)
        assert any("some_tool" in line and "not in lock file" in line for line in lines)

    def test_wasm_package_in_requirements(self, tmp_path):
        lockfile = _make_lockfile()
        req_path = tmp_path / "requirements.txt"
        req_path.write_text("numpy==2.2.5\n", encoding="utf-8")
        lines = sync_from_requirements_txt(lockfile, req_path)
        assert "✓ numpy: 2.2.5 (matches)" in lines

    def test_no_requirements_txt(self, tmp_path):
        lockfile = _make_lockfile()
        req_path = tmp_path / "requirements.txt"
        lines = sync_from_requirements_txt(lockfile, req_path)
        assert any("No requirements.txt" in line for line in lines)


class TestSyncFromPyprojectToml:
    def test_pinned_matching(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "pyproject.toml"
        path.write_text(
            '[project]\nname = "test"\ndependencies = ["markupsafe==2.1.5", "click==8.1.7"]\n',
            encoding="utf-8",
        )
        lines = sync_from_pyproject_toml(lockfile, path)
        assert "✓ markupsafe: 2.1.5 (matches)" in lines

    def test_unpinned_entry(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "pyproject.toml"
        path.write_text(
            '[project]\nname = "test"\ndependencies = ["markupsafe>=2.0"]\n',
            encoding="utf-8",
        )
        lines = sync_from_pyproject_toml(lockfile, path)
        assert any("not pinned" in line for line in lines)

    def test_bare_name(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "pyproject.toml"
        path.write_text(
            '[project]\nname = "test"\ndependencies = ["click"]\n',
            encoding="utf-8",
        )
        lines = sync_from_pyproject_toml(lockfile, path)
        lines_str = "\n".join(lines)
        assert "no version specifier" in lines_str

    def test_sync_group(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "pyproject.toml"
        path.write_text(
            '[project]\nname = "test"\ndependencies = []\n\n[project.optional-dependencies]\nbrowser = ["markupsafe==2.1.5"]\n',
            encoding="utf-8",
        )
        lines = sync_from_pyproject_toml(lockfile, path, sync_group="browser")
        assert "✓ markupsafe: 2.1.5 (matches)" in lines

    def test_sync_group_missing(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "pyproject.toml"
        path.write_text(
            '[project]\nname = "test"\ndependencies = []\n\n[project.optional-dependencies]\nbrowser = []\n',
            encoding="utf-8",
        )
        lines = sync_from_pyproject_toml(lockfile, path, sync_group="dev")
        assert any("dev" in line for line in lines)

    def test_no_project_dependencies(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "pyproject.toml"
        path.write_text('[project]\nname = "test"\n', encoding="utf-8")
        lines = sync_from_pyproject_toml(lockfile, path)
        assert any("No [project.dependencies]" in line for line in lines)

    def test_no_optional_dependencies(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "pyproject.toml"
        path.write_text('[project]\nname = "test"\n', encoding="utf-8")
        lines = sync_from_pyproject_toml(lockfile, path, sync_group="browser")
        assert any("optional-dependencies" in line for line in lines)


class TestSync:
    def test_both_files_exist(self, tmp_path):
        lockfile = _make_lockfile()
        (tmp_path / "requirements.txt").write_text("markupsafe==2.1.5\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\ndependencies = ["click==8.1.7"]\n', encoding="utf-8"
        )
        lines = sync(lockfile, tmp_path)
        assert any("requirements.txt" in line for line in lines)
        assert any("pyproject.toml" in line for line in lines)

    def test_only_pyproject_toml(self, tmp_path):
        lockfile = _make_lockfile()
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\ndependencies = ["markupsafe==2.1.5"]\n', encoding="utf-8"
        )
        lines = sync(lockfile, tmp_path)
        assert any("pyproject.toml" in line for line in lines)

    def test_neither_file(self, tmp_path):
        lockfile = _make_lockfile()
        (tmp_path / "pyproject.toml").write_text('[project]\nname="test"\n', encoding="utf-8")
        lines = sync(lockfile, tmp_path / "nonexistent")
        assert any("No requirements.txt" in line for line in lines)


class TestInstallRequirements:
    def test_uses_uv_when_available(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "requirements.txt"
        with (
            patch("webcompy.cli._lockfile_sync.shutil.which", return_value="/usr/bin/uv"),
            patch("webcompy.cli._lockfile_sync.subprocess.run") as mock_run,
        ):
            mock_run.return_value = types.SimpleNamespace(returncode=0)
            install_requirements(lockfile, path)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "uv"
        assert "pip" in call_args
        assert "-r" in call_args

    def test_uses_pip_when_uv_not_available(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "requirements.txt"
        with (
            patch("webcompy.cli._lockfile_sync.shutil.which", return_value=None),
            patch("webcompy.cli._lockfile_sync.subprocess.run") as mock_run,
        ):
            mock_run.return_value = types.SimpleNamespace(returncode=0)
            install_requirements(lockfile, path)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "-m" in call_args
        assert "pip" in call_args

    def test_propagates_nonzero_exit_code(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "requirements.txt"
        with (
            patch("webcompy.cli._lockfile_sync.shutil.which", return_value="/usr/bin/uv"),
            patch("webcompy.cli._lockfile_sync.subprocess.run") as mock_run,
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_run.return_value = types.SimpleNamespace(returncode=1)
            install_requirements(lockfile, path)
        assert exc_info.value.code == 1

    def test_exports_before_installing(self, tmp_path):
        lockfile = _make_lockfile()
        path = tmp_path / "requirements.txt"
        call_order = []

        def mock_export(lockfile_arg, path_arg):
            call_order.append("export")

        def mock_run_fn(*args, **kwargs):
            call_order.append("install")
            return types.SimpleNamespace(returncode=0)

        with (
            patch("webcompy.cli._lockfile_sync.export_requirements", side_effect=mock_export),
            patch("webcompy.cli._lockfile_sync.subprocess.run", side_effect=mock_run_fn),
            patch("webcompy.cli._lockfile_sync.shutil.which", return_value="/usr/bin/uv"),
        ):
            install_requirements(lockfile, path)
        assert call_order == ["export", "install"]


class TestResolveDependencies:
    def test_explicit_dependencies_not_overwritten(self, tmp_path):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component

        @define_component
        def Root(context):
            from webcompy.elements import html

            return html.DIV({}, "test")

        app = WebComPyApp(root_component=Root, config=AppConfig(dependencies=["numpy"]))
        resolve_dependencies(app)
        assert app.config.dependencies == ["numpy"]

    def test_auto_populate_from_project_dependencies(self, tmp_path):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component

        @define_component
        def Root(context):
            from webcompy.elements import html

            return html.DIV({}, "test")

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\ndependencies = ["flask>=3.0", "click==8.1.7"]\n',
            encoding="utf-8",
        )
        app_dir = tmp_path / "my_app"
        app_dir.mkdir()
        app = WebComPyApp(
            root_component=Root,
            config=AppConfig(app_package=app_dir, dependencies=None),
        )
        with patch("webcompy.cli._lockfile_sync.discover_project_root", return_value=tmp_path):
            resolve_dependencies(app)
        assert app.config.dependencies == ["flask", "click"]

    def test_auto_populate_from_optional_dependencies(self, tmp_path):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component

        @define_component
        def Root(context):
            from webcompy.elements import html

            return html.DIV({}, "test")

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\ndependencies = []\n\n[project.optional-dependencies]\nbrowser = ["numpy", "matplotlib"]\n',
            encoding="utf-8",
        )
        app_dir = tmp_path / "my_app"
        app_dir.mkdir()
        app = WebComPyApp(
            root_component=Root,
            config=AppConfig(app_package=app_dir, dependencies=None, dependencies_from="browser"),
        )
        with patch("webcompy.cli._lockfile_sync.discover_project_root", return_value=tmp_path):
            resolve_dependencies(app)
        assert app.config.dependencies == ["numpy", "matplotlib"]

    def test_no_pyproject_raises(self, tmp_path):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component

        @define_component
        def Root(context):
            from webcompy.elements import html

            return html.DIV({}, "test")

        app_dir = tmp_path / "no_project" / "my_app"
        app_dir.mkdir(parents=True)
        app = WebComPyApp(
            root_component=Root,
            config=AppConfig(app_package=app_dir, dependencies=None),
        )
        with pytest.raises(WebComPyCliException, match=r"pyproject\.toml"):
            resolve_dependencies(app)

    def test_missing_optional_group_raises(self, tmp_path):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component

        @define_component
        def Root(context):
            from webcompy.elements import html

            return html.DIV({}, "test")

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\ndependencies = []\n\n[project.optional-dependencies]\nbrowser = []\n',
            encoding="utf-8",
        )
        app_dir = tmp_path / "my_app"
        app_dir.mkdir()
        app = WebComPyApp(
            root_component=Root,
            config=AppConfig(app_package=app_dir, dependencies=None, dependencies_from="dev"),
        )
        with (
            patch("webcompy.cli._lockfile_sync.discover_project_root", return_value=tmp_path),
            pytest.raises(WebComPyCliException, match="dev"),
        ):
            resolve_dependencies(app)

    def test_version_specifiers_stripped(self, tmp_path):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component

        @define_component
        def Root(context):
            from webcompy.elements import html

            return html.DIV({}, "test")

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\ndependencies = ["flask>=3.0", "numpy==2.2.5"]\n',
            encoding="utf-8",
        )
        app_dir = tmp_path / "my_app"
        app_dir.mkdir()
        app = WebComPyApp(
            root_component=Root,
            config=AppConfig(app_package=app_dir, dependencies=None),
        )
        with patch("webcompy.cli._lockfile_sync.discover_project_root", return_value=tmp_path):
            resolve_dependencies(app)
        assert app.config.dependencies == ["flask", "numpy"]

    def test_dependencies_from_sync_group_mismatch_warning(self, tmp_path, capsys):
        from webcompy.app._app import WebComPyApp
        from webcompy.components._generator import define_component

        @define_component
        def Root(context):
            from webcompy.elements import html

            return html.DIV({}, "test")

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\n\n[project.optional-dependencies]\nbrowser = ["flask"]\n',
            encoding="utf-8",
        )
        app_dir = tmp_path / "my_app"
        app_dir.mkdir()
        app = WebComPyApp(
            root_component=Root,
            config=AppConfig(app_package=app_dir, dependencies=None, dependencies_from="browser"),
        )
        sync_config = LockfileSyncConfig(sync_group="deps")
        with patch("webcompy.cli._lockfile_sync.discover_project_root", return_value=tmp_path):
            resolve_dependencies(app, sync_config)
        captured = capsys.readouterr()
        assert "differs from" in captured.err


class TestLockArgParser:
    def test_export_flag(self):
        import sys

        from webcompy.cli._argparser import get_params

        original_argv = sys.argv
        sys.argv = ["webcompy", "lock", "--export"]
        try:
            command, args = get_params()
            assert command == "lock"
            assert args.get("export") is True
            assert args.get("sync") is not True
            assert args.get("install") is not True
        finally:
            sys.argv = original_argv

    def test_sync_flag(self):
        import sys

        from webcompy.cli._argparser import get_params

        original_argv = sys.argv
        sys.argv = ["webcompy", "lock", "--sync"]
        try:
            command, args = get_params()
            assert command == "lock"
            assert args.get("sync") is True
            assert args.get("export") is not True
            assert args.get("install") is not True
        finally:
            sys.argv = original_argv

    def test_install_flag(self):
        import sys

        from webcompy.cli._argparser import get_params

        original_argv = sys.argv
        sys.argv = ["webcompy", "lock", "--install"]
        try:
            command, args = get_params()
            assert command == "lock"
            assert args.get("install") is True
            assert args.get("export") is not True
            assert args.get("sync") is not True
        finally:
            sys.argv = original_argv

    def test_no_flags(self):
        import sys

        from webcompy.cli._argparser import get_params

        original_argv = sys.argv
        sys.argv = ["webcompy", "lock"]
        try:
            command, args = get_params()
            assert command == "lock"
            assert args.get("export") is not True
            assert args.get("sync") is not True
            assert args.get("install") is not True
        finally:
            sys.argv = original_argv

    def test_mutually_exclusive_flags(self):
        import sys

        from webcompy.cli._argparser import get_params

        for combo in [["--export", "--sync"], ["--export", "--install"], ["--sync", "--install"]]:
            original_argv = sys.argv
            sys.argv = ["webcompy", "lock", *combo]
            try:
                with pytest.raises(SystemExit):
                    get_params()
            finally:
                sys.argv = original_argv
