from pathlib import Path

from webcompy.app import AppConfig

app_import_path = "docs_src.bootstrap:app"
app_config = AppConfig(
    app_package=Path(__file__).parent / "docs_src",
    base_url="/",
    dependencies=[
        "numpy",
        "matplotlib",
    ],
)
