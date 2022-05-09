from webcompy.reactive import Reactive
from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from webcompy.elements import DOMEvent


@define_component
def InOutSample(_: ComponentContext[RouterContext]):
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
