from pathlib import Path

from webcompy.app import AppConfig

app_import_path = "app.bootstrap:app"
app_config = AppConfig(app_package=Path(__file__).parent / "app", base_url="/")
