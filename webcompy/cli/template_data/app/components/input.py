from webcompy.components import ComponentContext, define_component
from webcompy.elements import DOMEvent, html
from webcompy.reactive import Reactive
from webcompy.router import RouterContext


@define_component
def InOutSample(context: ComponentContext[RouterContext]):
    context.set_title("Text Input Sample - WebCompy Template")

    text = Reactive("")

    def on_input(ev: DOMEvent):
        text.value = ev.target.value

    return html.DIV(
        {},
        html.H4({}, "Text Input Sample"),
        html.P(
            {},
            "Input: ",
            html.INPUT(
                {"type": "text", "@input": on_input},
            ),
        ),
        html.P(
            {},
            "Output: ",
            text,
        ),
    )
