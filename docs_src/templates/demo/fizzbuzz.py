from webcompy.components import (
    TypedComponentBase,
    component_class,
    component_template,
    on_before_rendering,
)
from webcompy.elements import DOMEvent, html, repeat, switch
from webcompy.reactive import Reactive, computed, computed_property
from webcompy.reactive._dict import ReactiveDict


@component_class
class Fizzbuzz(TypedComponentBase(props_type=None)):
    def __init__(self) -> None:
        self.opened = Reactive(True)
        self.fizzbuzz_dict: ReactiveDict[int, str] = ReactiveDict()
        self._next_n = Reactive(1)

    @computed_property
    def toggle_button_text(self):
        return "Hide" if self.opened.value else "Open"

    def _fizzbuzz(self, n: int) -> str:
        if n % 15 == 0:
            return "FizzBuzz"
        elif n % 5 == 0:
            return "Fizz"
        elif n % 3 == 0:
            return "Buzz"
        else:
            return str(n)

    def add(self, ev: DOMEvent):
        n = self._next_n.value
        self.fizzbuzz_dict[n] = self._fizzbuzz(n)
        self._next_n.value = n + 1

    def pop(self, ev: DOMEvent):
        if len(self.fizzbuzz_dict.value) > 0:
            last_key = list(self.fizzbuzz_dict.value.keys())[-1]
            self.fizzbuzz_dict.pop(last_key)
            self._next_n.value -= 1

    def toggle(self, ev: DOMEvent):
        self.opened.value = not self.opened.value

    @on_before_rendering
    def on_before_rendering(self):
        self.fizzbuzz_dict.clear()
        self._next_n.value = 1
        for n in range(1, 11):
            self.fizzbuzz_dict[n] = self._fizzbuzz(n)
            self._next_n.value = n + 1

    @component_template
    def template(self):
        return html.DIV(
            {},
            html.P(
                {},
                html.BUTTON(
                    {
                        "@click": self.add,
                        "disabled": computed(lambda: not self.opened.value),
                    },
                    "Add",
                ),
                html.BUTTON(
                    {
                        "@click": self.pop,
                        "disabled": computed(lambda: not self.opened.value),
                    },
                    "Pop",
                ),
                html.BUTTON(
                    {"@click": self.toggle},
                    self.toggle_button_text,
                ),
            ),
            html.P(
                {},
                "Count: ",
                computed(lambda: str(len(self.fizzbuzz_dict.value))),
            ),
            switch(
                {
                    "case": self.opened,
                    "generator": lambda: html.DIV(
                        {},
                        html.UL(
                            {},
                            repeat(
                                self.fizzbuzz_dict,
                                lambda k, v: html.LI({}, v),
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
