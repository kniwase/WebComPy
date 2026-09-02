import docs_app.app as app_module
from webcompy_cli.config import LockfileSyncConfig, WebComPyBuildConfig, WebComPyServerConfig

config = WebComPyBuildConfig(
    app_module,
    dependencies=[],
    standalone=True,
    wheel_mode="split",
    resource_transfer="all-text",
    dist="dist",
    static_files_dir="static",
    lockfile_sync_config=LockfileSyncConfig(sync_group="browser"),
    server=WebComPyServerConfig(port=8080),
)
