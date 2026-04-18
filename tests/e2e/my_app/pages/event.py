from webcompy.components import ComponentContext, define_component
from webcompy.elements import DomNodeRef, html
from webcompy.reactive import Reactive, computed


@define_component
def EventPage(context: ComponentContext[None]):
    context.set_title("Event - E2E")

    click_count = Reactive(0)
    input_ref = DomNodeRef()
    input_value = Reactive("")
    checkbox_ref = DomNodeRef()
    checkbox_state = Reactive(False)

    def on_click(_):
        click_count.value += 1

    def on_submit(_):
        input_value.value = input_ref.value

    def on_checkbox_change(_):
        checkbox_state.value = checkbox_ref.checked

    return html.DIV(
        {"data-testid": "event-page"},
        html.H2({}, "Event Tests"),
        html.P({}, "Click count: ", html.SPAN({"data-testid": "click-count"}, click_count)),
        html.BUTTON({"data-testid": "click-btn", "@click": on_click}, "Click Me"),
        html.DIV(
            {},
            html.INPUT({"data-testid": "text-input", ":ref": input_ref, "type": "text"}),
            html.BUTTON({"data-testid": "submit-btn", "@click": on_submit}, "Submit"),
            html.SPAN({"data-testid": "input-value"}, input_value),
        ),
        html.DIV(
            {},
            html.INPUT(
                {
                    "data-testid": "checkbox-input",
                    "type": "checkbox",
                    ":ref": checkbox_ref,
                    "@change": on_checkbox_change,
                },
            ),
            html.SPAN(
                {"data-testid": "checkbox-state"}, computed(lambda: "checked" if checkbox_state.value else "unchecked")
            ),
        ),
    )
