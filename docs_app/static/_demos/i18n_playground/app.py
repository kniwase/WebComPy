from typing import Any

from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.i18n import I18N_KEY, I18nManager, use_i18n
from webcompy.signal import use_computed, use_state

_I18N_CATALOGS: dict[str, dict[str, object]] = {
    "en": {
        "demo": {
            "current": "Current locale: {locale}",
            "greeting": "Hello, {name}!",
            "notice": "This demo renders with {framework}.",
            "items": {"one": "{count} item", "other": "{count} items"},
            "count_tip": "Change the item count:",
        },
    },
    "ja": {
        "demo": {
            "current": "現在のロケール: {locale}",
            "greeting": "こんにちは、{name} さん!",
            "notice": "このデモは {framework} で描画されています。",
            "items": {"other": "{count} 個のアイテム"},
            "count_tip": "アイテム数を変えてみる:",
        },
    },
}


def make_i18n_manager() -> I18nManager:
    return I18nManager(
        _I18N_CATALOGS,
        default_locale="en",
        supported_locales={"en", "ja"},
        persist=False,
    )


@define_component()
def I18nPlaygroundApp(_: ComponentContext[None]):
    _, t, controller = use_i18n()
    count = use_state(lambda: 3)

    def _adjust(delta: int):
        def _on_click(_ev: Any) -> None:
            count.value = max(1, count.value + delta)

        return _on_click

    return html.DIV(
        {"class": "i18n-demo"},
        html.H1({}, "Internationalization (i18n)"),
        html.DIV(
            {"class": "i18n-section"},
            html.DIV(
                {"class": "i18n-switcher"},
                html.BUTTON({"type": "button", "@click": lambda _ev: controller.set("en")}, "English"),
                html.BUTTON({"type": "button", "@click": lambda _ev: controller.set("ja")}, "日本語"),
            ),
            html.P({"class": "i18n-current"}, use_computed(lambda: t("demo.current", locale=controller.locale))),
        ),
        html.DIV(
            {"class": "i18n-section"},
            html.P({}, use_computed(lambda: t("demo.notice", framework="WebComPy"))),
            html.P({}, use_computed(lambda: t("demo.greeting", name="WebComPy user"))),
        ),
        html.DIV(
            {"class": "i18n-section"},
            html.P({}, use_computed(lambda: t("demo.count_tip"))),
            html.DIV(
                {"class": "i18n-count-controls"},
                html.BUTTON({"type": "button", "@click": _adjust(-1)}, "-"),
                html.SPAN({"class": "i18n-count"}, use_computed(lambda: str(count.value))),
                html.BUTTON({"type": "button", "@click": _adjust(1)}, "+"),
            ),
            html.P({"class": "i18n-items"}, use_computed(lambda: t("demo.items", count=count.value))),
        ),
    )


I18nPlaygroundApp.scoped_style = {
    ".i18n-demo": {
        "font-family": "var(--font-sans, sans-serif)",
        "padding": "var(--space-3)",
        "color": "var(--color-fg)",
        "max-width": "32rem",
    },
    ".i18n-demo h1": {
        "margin": "0 0 var(--space-3) 0",
        "font-size": "var(--font-size-xl, 1.25rem)",
    },
    ".i18n-section": {
        "padding": "var(--space-3)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-card)",
        "margin-bottom": "var(--space-3)",
    },
    ".i18n-switcher": {
        "display": "flex",
        "gap": "var(--space-2)",
        "margin-bottom": "var(--space-2)",
    },
    ".i18n-count-controls": {
        "display": "flex",
        "align-items": "center",
        "gap": "var(--space-3)",
        "margin": "var(--space-2) 0",
    },
    ".i18n-count": {
        "font-size": "var(--font-size-lg, 1.125rem)",
        "font-weight": "600",
        "min-width": "2rem",
        "text-align": "center",
    },
    ".i18n-items": {
        "font-size": "var(--font-size-lg, 1.125rem)",
        "font-weight": "600",
        "margin": "0",
    },
    ".i18n-demo button": {
        "padding": "0.35rem 0.75rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
        "cursor": "pointer",
    },
}


@define_component()
def I18nPlaygroundRoot(context: ComponentContext[None]):
    context.provide(I18N_KEY, make_i18n_manager)
    return I18nPlaygroundApp(None)


app = WebComPyApp(root_component=I18nPlaygroundRoot)
app.run()
