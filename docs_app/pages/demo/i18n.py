from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.i18n import use_i18n
from webcompy.router import RouterContext
from webcompy.signal import use_computed, use_state

from ...components.ui import DocsButton, DocsSection


@define_component()
def I18nDemoPage(context: ComponentContext[RouterContext]):
    context.set_title("i18n - WebComPy Demo")
    _, t, controller = use_i18n()
    count = use_state(lambda: 3)

    def _set_count(amount: int):
        def _on_click(_ev):
            count.value = max(1, count.value + amount)

        return _on_click

    return html.DIV(
        {"class": "page-container"},
        html.H1({"class": "page-title"}, "Internationalization (i18n)"),
        html.P(
            {"class": "page-lead"},
            "Translations resolve against a reactive locale signal, so switching "
            "locale re-renders every rendered translation automatically.",
        ),
        DocsSection(
            {"heading": "Locale switcher"},
            slots={
                "default": lambda: html.DIV(
                    {"class": "i18n-panel"},
                    html.DIV(
                        {"class": "i18n-switcher"},
                        DocsButton({"text": "English", "onclick": lambda _ev: controller.set("en")}),
                        DocsButton({"text": "日本語", "onclick": lambda _ev: controller.set("ja")}),
                    ),
                    html.P({}, use_computed(lambda: t("demo.current", locale=controller.locale))),
                )
            },
        ),
        DocsSection(
            {"heading": "Interpolation"},
            slots={
                "default": lambda: html.P({}, use_computed(lambda: t("demo.notice", framework="WebComPy"))),
            },
        ),
        DocsSection(
            {"heading": "Greeting"},
            slots={
                "default": lambda: html.P({}, use_computed(lambda: t("demo.greeting", name="WebComPy user"))),
            },
        ),
        DocsSection(
            {"heading": "Pluralization"},
            slots={
                "default": lambda: html.DIV(
                    {"class": "i18n-panel"},
                    html.P({}, use_computed(lambda: t("demo.count_tip"))),
                    html.DIV(
                        {"class": "i18n-count-controls"},
                        DocsButton({"text": "-", "onclick": _set_count(-1)}),
                        html.SPAN(
                            {"class": "i18n-count"},
                            use_computed(lambda: str(count.value)),
                        ),
                        DocsButton({"text": "+", "onclick": _set_count(1)}),
                    ),
                    html.P({"class": "i18n-translated"}, use_computed(lambda: t("demo.items", count=count.value))),
                )
            },
        ),
    )


I18nDemoPage.scoped_style = {
    ".page-title": {
        "font-size": "var(--font-size-2xl)",
        "font-weight": "700",
        "margin-bottom": "var(--space-2)",
    },
    ".page-lead": {
        "color": "var(--color-fg-muted)",
        "margin-bottom": "var(--space-4)",
    },
    ".i18n-panel": {
        "display": "flex",
        "flex-direction": "column",
        "gap": "var(--space-3)",
    },
    ".i18n-switcher": {
        "display": "flex",
        "gap": "var(--space-2)",
        "flex-wrap": "wrap",
    },
    ".i18n-count-controls": {
        "display": "flex",
        "align-items": "center",
        "gap": "var(--space-3)",
    },
    ".i18n-count": {
        "font-size": "var(--font-size-xl)",
        "font-weight": "600",
        "min-width": "2rem",
        "text-align": "center",
    },
    ".i18n-translated": {
        "font-size": "var(--font-size-lg)",
        "font-weight": "500",
    },
}
