from webcompy.components import (
    ComponentContext,
    define_component,
    on_before_rendering,
)
from webcompy.elements import DOMEvent, html, repeat, switch
from webcompy.signal import ReactiveDict, Signal, computed


@define_component
def Fizzbuzz(context: ComponentContext[None]):
    opened = Signal(True)
    fizzbuzz_dict: ReactiveDict[int, str] = ReactiveDict()
    _next_n = Signal(1)

    @computed
    def toggle_button_text():
        return "Hide" if opened.value else "Open"

    def _fizzbuzz(n: int) -> str:
        if n % 15 == 0:
            return "FizzBuzz"
        elif n % 5 == 0:
            return "Fizz"
        elif n % 3 == 0:
            return "Buzz"
        else:
            return str(n)

    def add(ev: DOMEvent):
        n = _next_n.value
        fizzbuzz_dict[n] = _fizzbuzz(n)
        _next_n.value = n + 1

    def pop(ev: DOMEvent):
        if len(fizzbuzz_dict.value) > 0:
            last_key = list(fizzbuzz_dict.value.keys())[-1]
            fizzbuzz_dict.pop(last_key)
            _next_n.value -= 1

    def toggle(ev: DOMEvent):
        opened.value = not opened.value

    @on_before_rendering
    def reset():
        fizzbuzz_dict.clear()
        _next_n.value = 1
        for n in range(1, 11):
            fizzbuzz_dict[n] = _fizzbuzz(n)
            _next_n.value = n + 1

    return html.DIV(
        {},
        html.P(
            {},
            html.BUTTON(
                {
                    "@click": add,
                    "disabled": computed(lambda: not opened.value),
                },
                "Add",
            ),
            html.BUTTON(
                {
                    "@click": pop,
                    "disabled": computed(lambda: not opened.value),
                },
                "Pop",
            ),
            html.BUTTON(
                {"@click": toggle},
                toggle_button_text,
            ),
        ),
        html.P(
            {},
            "Count: ",
            computed(lambda: str(len(fizzbuzz_dict.value))),
        ),
        switch(
            {
                "case": opened,
                "generator": lambda: html.DIV(
                    {},
                    html.UL(
                        {},
                        repeat(
                            fizzbuzz_dict,
                            lambda v, k: html.LI({}, v),
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
