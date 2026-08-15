from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import use_computed, use_state


@define_component("two-way-binding-page")
def TwoWayBindingPage(context: ComponentContext[None]):
    context.set_title("Two-Way Binding - E2E")

    text = use_state(lambda: "hello")
    number = use_state(lambda: 5)
    flag = use_state(lambda: False)
    choice = use_state(lambda: "a")
    body = use_state(lambda: "initial")

    def set_text(_):
        text.value = "reset"

    return html.DIV(
        {"data-testid": "two-way-binding-page"},
        html.H2({}, "Two-Way Binding Tests"),
        html.DIV(
            {},
            html.INPUT({"data-testid": "bind-text", ":bind": text}),
            html.SPAN({"data-testid": "bind-text-value"}, text),
            html.BUTTON({"data-testid": "set-text-btn", "@click": set_text}, "Reset Text"),
        ),
        html.DIV(
            {},
            html.INPUT({"data-testid": "bind-number", "type": "number", ":bind": number}),
            html.SPAN({"data-testid": "bind-number-value"}, number),
        ),
        html.DIV(
            {},
            html.INPUT({"data-testid": "bind-checkbox", "type": "checkbox", ":bind": flag}),
            html.SPAN(
                {"data-testid": "bind-checkbox-value"},
                use_computed(lambda: "checked" if flag.value else "unchecked"),
            ),
        ),
        html.DIV(
            {},
            html.INPUT({"data-testid": "bind-radio-a", "type": "radio", "value": "a", ":bind": choice}),
            html.INPUT({"data-testid": "bind-radio-b", "type": "radio", "value": "b", ":bind": choice}),
            html.SPAN({"data-testid": "bind-radio-value"}, choice),
        ),
        html.DIV(
            {},
            html.TEXTAREA({"data-testid": "bind-textarea", ":bind": body}),
            html.SPAN({"data-testid": "bind-textarea-value"}, body),
        ),
    )
