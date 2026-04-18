from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, switch
from webcompy.reactive import Reactive, computed


@define_component
def SwitchPage(context: ComponentContext[None]):
    context.set_title("Switch - E2E")

    flag = Reactive(True)

    def toggle(_):
        flag.value = not flag.value

    return html.DIV(
        {"data-testid": "switch-page"},
        html.H2({}, "Switch Tests"),
        html.BUTTON({"data-testid": "toggle-btn", "@click": toggle}, "Toggle"),
        html.SPAN({"data-testid": "flag-state"}, computed(lambda: "on" if flag.value else "off")),
        switch(
            {
                "case": flag,
                "generator": lambda: html.DIV({"data-testid": "switch-on"}, "Switch is ON"),
            },
            default=lambda: html.DIV({"data-testid": "switch-off"}, "Switch is OFF"),
        ),
    )
