from webcompy.components import ComponentContext, define_component
from webcompy.di import InjectKey, inject, provide
from webcompy.elements import html

from ..keys import AppThemeKey

ThemeKey = InjectKey[str]("e2e-theme")


@define_component
def DiProviderWrapper(context: ComponentContext[None]):
    context.set_title("DI - E2E")
    provide(ThemeKey, "dark-theme")
    return html.DIV(
        {"data-testid": "di-provider-page"},
        html.H2({}, "DI Provide/Inject"),
        DiChildComponent(None),
    )


@define_component
def DiChildComponent(context: ComponentContext[None]):
    theme = inject(ThemeKey)
    return html.SPAN({"data-testid": "child-theme"}, theme)


@define_component
def DiInjectPage(context: ComponentContext[None]):
    context.set_title("DI Inject - E2E")
    app_theme = inject(AppThemeKey)
    return html.DIV(
        {"data-testid": "di-inject-page"},
        html.SPAN({"data-testid": "injected-app-theme"}, app_theme),
    )
