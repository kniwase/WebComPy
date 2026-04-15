from pathlib import Path

from webcompy.cli import WebComPyConfig


class TestWebComPyConfig:
    def test_app_package_path_from_string(self):
        config = WebComPyConfig(app_package="myapp")
        assert config.app_package_path == Path("./myapp").absolute()

    def test_app_package_path_from_path(self, tmp_path):
        app_dir = tmp_path / "myapp"
        app_dir.mkdir()
        config = WebComPyConfig(app_package=app_dir)
        assert config.app_package_path == app_dir.absolute()

    def test_base_normalization(self):
        config = WebComPyConfig(app_package="myapp", base="/WebComPy")
        assert config.base == "/WebComPy/"

    def test_base_root(self):
        config = WebComPyConfig(app_package="myapp", base="/")
        assert config.base == "/"

    def test_base_no_slashes(self):
        config = WebComPyConfig(app_package="myapp", base="MyApp")
        assert config.base == "/MyApp/"

    def test_server_port_default(self):
        config = WebComPyConfig(app_package="myapp")
        assert config.server_port == 8080

    def test_server_port_custom(self):
        config = WebComPyConfig(app_package="myapp", server_port=3000)
        assert config.server_port == 3000

    def test_static_files_dir_path_from_string(self):
        config = WebComPyConfig(app_package="myapp")
        assert config.static_files_dir_path == Path("./myapp").absolute().parent / "static"

    def test_static_files_dir_path_from_path(self, tmp_path):
        app_dir = tmp_path / "myapp"
        app_dir.mkdir()
        static_dir = tmp_path / "custom_static"
        static_dir.mkdir()
        config = WebComPyConfig(app_package=app_dir, static_files_dir=static_dir)
        assert config.static_files_dir_path == static_dir.absolute()
        assert config.app_package_path == app_dir.absolute()

    def test_static_files_dir_path_does_not_overwrite_app_package(self, tmp_path):
        app_dir = tmp_path / "myapp"
        app_dir.mkdir()
        static_dir = tmp_path / "static_files"
        static_dir.mkdir()
        config = WebComPyConfig(app_package=app_dir, static_files_dir=static_dir)
        assert config.app_package_path == app_dir.absolute()
        assert config.static_files_dir_path == static_dir.absolute()

    def test_dependencies_default(self):
        config = WebComPyConfig(app_package="myapp")
        assert config.dependencies == []

    def test_dependencies_custom(self):
        config = WebComPyConfig(app_package="myapp", dependencies=["numpy", "matplotlib"])
        assert config.dependencies == ["numpy", "matplotlib"]

    def test_dist_default(self):
        config = WebComPyConfig(app_package="myapp")
        assert config.dist == "dist"
