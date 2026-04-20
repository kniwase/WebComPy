from pathlib import Path

from webcompy.app import AppConfig

app_import_path = "my_app.bootstrap:app"
app_config = AppConfig(app_package=Path(__file__).parent / "my_app", base_url="/")
