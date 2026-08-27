from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, switch
from webcompy.signal import use_computed, use_state


@define_component()
def SwitchPage(context: ComponentContext[None]):
    context.set_title("Switch - E2E")

    flag = use_state(lambda: True)

    def toggle(_):
        flag.value = not flag.value

    return html.DIV(
        {"data-testid": "switch-page"},
        html.H2({}, "Switch Tests"),
        html.BUTTON({"data-testid": "toggle-btn", "@click": toggle}, "Toggle"),
        html.SPAN({"data-testid": "flag-state"}, use_computed(lambda: "on" if flag.value else "off")),
        switch(
            {
                "case": flag,
                "generator": lambda: html.DIV({"data-testid": "switch-on"}, "Switch is ON"),
            },
            default=lambda: html.DIV({"data-testid": "switch-off"}, "Switch is OFF"),
        ),
    )
