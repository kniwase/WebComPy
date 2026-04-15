from pathlib import Path

from webcompy.cli import WebComPyConfig

config = WebComPyConfig(
    app_package=Path(__file__).parent / "app",
    base="/WebComPy",
    server_port=8088,
    dependencies=[],
)
