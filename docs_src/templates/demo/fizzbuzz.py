from webcompy.reactive import Reactive, computed_property
from webcompy.elements import html, repeat, switch
from webcompy.components import (
    TypedComponentBase,
    component_class,
    on_before_rendering,
    component_template,
)
from webcompy.elements import DOMEvent


@component_class
class Fizzbuzz(TypedComponentBase(props_type=None)):
    def __init__(self) -> None:
        self.opened = Reactive(True)
        self.count = Reactive(10)

    @computed_property
    def fizzbuzz_list(self):
        li: list[str] = []
        for n in range(1, self.count.value + 1):
            if n % 15 == 0:
                li.append("FizzBuzz")
            elif n % 5 == 0:
                li.append("Fizz")
            elif n % 3 == 0:
                li.append("Buzz")
            else:
                li.append(str(n))
        return li

    @computed_property
    def toggle_button_text(self):
        return "Hide" if self.opened.value else "Open"

    def add(self, ev: DOMEvent):
        self.count.value += 1

    def pop(self, ev: DOMEvent):
        if self.count.value > 0:
            self.count.value -= 1

    def toggle(self, ev: DOMEvent):
        self.opened.value = not self.opened.value

    @on_before_rendering
    def on_before_rendering(self):
        self.count.value = 10

    @component_template
    def template(self):
        return html.DIV(
            {},
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
                    "generator": lambda: html.DIV(
                        {},
                        html.UL(
                            {},
                            repeat(
                                self.fizzbuzz_list,
                                lambda s: html.LI({}, s),
                            ),
                        ),
                    ),
                },
                default=lambda: html.DIV(
                    {},
                    "FizzBuzz Hidden",
                ),
            ),
        )


Fizzbuzz.scoped_style = {
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
    "button": {
        "display": "inline-block",
        "text-decoration": "none",
        "border": "solid 2px #668ad8",
        "border-radius": "3px",
        "transition": "0.2s",
        "color": "black",
    },
    "button:hover": {
        "background": "#668ad8",
        "color": "white",
    },
}
