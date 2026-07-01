import app.app as app_module

from webcompy_cli.config import WebComPyBuildConfig, WebComPyServerConfig

config = WebComPyBuildConfig(
    app_module,
    dependencies=None,
    dependencies_from=None,
    server=WebComPyServerConfig(port=8080),
)
