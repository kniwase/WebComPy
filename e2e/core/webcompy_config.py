import my_app.app as app_module

from webcompy_cli.config import WebComPyBuildConfig, WebComPyServerConfig

config = WebComPyBuildConfig(
    app_module,
    dependencies=["aiofiles"],
    server=WebComPyServerConfig(port=8088),
    static_files_dir="../static",
)
