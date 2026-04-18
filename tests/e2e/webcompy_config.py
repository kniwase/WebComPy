from pathlib import Path

from webcompy.cli import WebComPyConfig

config = WebComPyConfig(
    app_package=Path(__file__).parent / "my_app",
    base="/",
    server_port=8088,
    dependencies=[],
)
