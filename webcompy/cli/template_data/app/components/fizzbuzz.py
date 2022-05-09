from webcompy.reactive import Reactive, computed_property, computed
from webcompy.elements import html, repeat, switch
from webcompy.components import (
    define_component,
    ComponentContext,
    TypedComponentBase,
    component_class,
    on_before_rendering,
    component_template,
)
from webcompy.router import RouterContext
from webcompy.elements import DOMEvent


@define_component
def FizzbuzzList(context: ComponentContext[Reactive[int]]):
    @computed
    def numbers():
        li: list[str] = []
        for n in range(1, context.props.value + 1):
            if n % 15 == 0:
                li.append("FizzBuzz")
            elif n % 5 == 0:
                li.append("Fizz")
            elif n % 3 == 0:
                li.append("Buzz")
            else:
                li.append(str(n))
        return li

    return html.DIV(
        {},
        html.UL(
            {},
            repeat(numbers, lambda s: html.LI({}, s)),
        ),
    )


FizzbuzzList.scoped_style = {
    "ul": {
        "border": "dashed 2px #668ad8",
        "background": "#f1f8ff",
        "padding": "0.5em 0.5em 0.5em 2em",
    },
    "ul > li:nth-child(3n)": {
        "color": "red",
    },
    "ul > li:nth-child(5n)": {
        "color": "blue",
    },
    "ul > li:nth-child(15n)": {
        "color": "purple",
    },
}


@component_class
class Fizzbuzz(TypedComponentBase(props_type=RouterContext)):
    def __init__(self) -> None:
        self.opened = Reactive(True)
        self.count = Reactive(10)

    @computed_property
    def toggle_button_text(self):
        return "Hide" if self.opened.value else "Open"

    @on_before_rendering
    def on_before_rendering(self):
        self.count.value = 10

    def add(self, ev: DOMEvent):
        self.count.value += 1

    def pop(self, ev: DOMEvent):
        if self.count.value > 0:
            self.count.value -= 1

    def toggle(self, ev: DOMEvent):
        self.opened.value = not self.opened.value

    @component_template
    def template(self):
        return html.DIV(
            {},
            html.H2(
                {},
                "FizzBuzz",
            ),
            html.P(
                {},
                html.BUTTON(
                    {"@click": self.toggle},
                    self.toggle_button_text,
                ),
                html.BUTTON(
                    {"@click": self.add},
                    "Add",
                ),
                html.BUTTON(
                    {"@click": self.pop},
                    "Pop",
                ),
            ),
            html.P(
                {},
                "Count: ",
                self.count,
            ),
            switch(
                {
                    "case": self.opened,
                    "generator": lambda: FizzbuzzList(props=self.count),
                },
                default=lambda: html.DIV(
                    {},
                    "FizzBuzz Hidden",
                ),
            ),
        )
