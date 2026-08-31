import os

import pwa_app.app as app_module

from webcompy_cli.config import ManifestConfig, PWAConfig, RuntimeCachingRule, WebComPyBuildConfig

config = WebComPyBuildConfig(
    app_module,
    dependencies=[],
    static_files_dir="../static",
    version=os.environ.get("PWA_VERSION", "1.0.0"),
    pwa=PWAConfig(
        enabled=True,
        manifest=ManifestConfig(name="PWA E2E App", short_name="PWA", theme_color="#1d4ed8"),
        fallback_path="pwa_offline.html",
        runtime=[RuntimeCachingRule(pattern="/about/", strategy="cache-first")],
    ),
)
