import loading_app.app as app_module

from webcompy_cli.config import WebComPyBuildConfig

config = WebComPyBuildConfig(
    app_module,
    dependencies=[],
    static_files_dir="../static",
)
