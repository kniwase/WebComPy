from pathlib import Path

from webcompy.app import AppConfig

app_import_path = "docs_app.bootstrap:app"
app_config = AppConfig(
    app_package=Path(__file__).parent,
    base_url="/",
    dependencies=None,
    dependencies_from="browser",
    standalone=True,  # Generate docs with local runtime assets for offline capability
)
