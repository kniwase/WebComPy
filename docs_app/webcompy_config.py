from pathlib import Path

from webcompy.app import AppConfig, PluginScript

app_import_path = "docs_app.bootstrap:app"
app_config = AppConfig(
    app_package=Path(__file__).parent,
    base_url="/",
    dependencies=None,
    dependencies_from="browser",
    standalone=True,
    scripts=[
        PluginScript(
            attrs={
                "type": "text/javascript",
                "src": "https://cdnjs.cloudflare.com/ajax/libs/eruda/2.4.1/eruda.min.js",
            },
            in_head=True,
            condition="new URLSearchParams(location.search).get('debug') === 'True'",
        ),
        PluginScript(
            script="eruda.init();",
            condition="new URLSearchParams(location.search).get('debug') === 'True'",
        ),
    ],
)
