from pathlib import Path

from webcompy.cli import WebComPyConfig

# NOTE: WebComPyConfig is deprecated. Use AppConfig with WebComPyApp instead.
config = WebComPyConfig(app_package=Path(__file__).parent / "app", base="/")
