from pathlib import Path

from webcompy.app import AppConfig

app_import_path = "docs_app.bootstrap:app"
# Uses split mode to dogfood two-wheel serving and independently cache the
# framework wheel across docs deployments.
app_config = AppConfig(
    app_package=Path(__file__).parent,
    base_url="/",
    dependencies=None,
    dependencies_from="browser",
    standalone=True,
    plugins=["docs_app.plugins:ErudaPlugin"],
    wheel_mode="split",
)
