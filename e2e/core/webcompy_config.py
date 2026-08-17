import my_app.app as app_module
import my_app.sse_server
import my_app.ws_server

from webcompy_cli.config import WebComPyBuildConfig, WebComPyServerConfig

config = WebComPyBuildConfig(
    app_module,
    dependencies=["aiofiles"],
    server=WebComPyServerConfig(
        port=8088,
        mounts=lambda: {"/sse": my_app.sse_server.create_sse_app(), "/ws": my_app.ws_server.create_ws_app()},
    ),
    static_files_dir="../static",
)
