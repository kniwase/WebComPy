from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.i18n import I18N_KEY, I18nManager

from .layout import DocsRoot
from .router import router

_I18N_CATALOGS: dict[str, dict[str, object]] = {
    "en": {
        "demo": {
            "current": "Current locale: {locale}",
            "greeting": "Hello, {name}!",
            "notice": "This demo renders with {framework}.",
            "items": {"one": "{count} item", "other": "{count} items"},
            "switcher": "Locale",
            "count_tip": "Change the item count:",
        },
    },
    "ja": {
        "demo": {
            "current": "現在のロケール: {locale}",
            "greeting": "こんにちは、{name} さん！",  # noqa: RUF001
            "notice": "このデモは {framework} で描画されています。",
            "items": {"other": "{count} 個のアイテム"},
            "switcher": "言語",
            "count_tip": "アイテム数を変えてみる:",
        },
    },
}


def _make_i18n_manager() -> I18nManager:
    return I18nManager(_I18N_CATALOGS, default_locale="en", supported_locales={"en", "ja"})


app = WebComPyApp(
    root_component=DocsRoot,
    router=router,
    config=WebComPyAppConfig(base_url="/", plugins=["docs_app.plugins:ErudaPlugin"]),
)
app.provide(I18N_KEY, _make_i18n_manager)
app.set_head(
    {
        "title": "WebComPy - Python Frontend Framework",
        "meta": {
            "charset": {
                "charset": "utf-8",
            },
            "viewport": {
                "name": "viewport",
                "content": "width=device-width, initial-scale=1.0",
            },
            "description": {
                "name": "description",
                "content": "WebComPy is Python frontend framework on Browser",
            },
            "keywords": {
                "name": "keywords",
                "content": "python,framework,browser,frontend,client-side",
            },
            "google-site-verification": {
                "name": "google-site-verification",
                "content": "qRIOGfRioPW7wInrUcunEcZZICOQK1VGZgsP-mlGicA",
            },
        },
        "link": [
            {
                "rel": "stylesheet",
                "href": "/styles/components.css",
            },
            {
                "rel": "stylesheet",
                "href": "/_webcompy-ui/prose.css",
            },
        ],
    }
)
