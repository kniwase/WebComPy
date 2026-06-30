from webcompy.components import (
    ComponentContext,
    define_component,
    on_before_rendering,
)
from webcompy.elements import DOMEvent, html, repeat, switch
from webcompy.router import RouterContext
from webcompy.signal import Signal, computed


@define_component
def FizzbuzzList(context: ComponentContext[Signal[int]]):
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


@define_component
def Fizzbuzz(context: ComponentContext[RouterContext]):
    context.set_title("FizzBuzz - WebComPy Template")

    opened = Signal(True)
    count = Signal(10)

    @computed
    def toggle_button_text():
        return "Hide" if opened.value else "Open"

    @on_before_rendering
    def reset_count():
        count.value = 10

    def add(ev: DOMEvent):
        count.value += 1

    def pop(ev: DOMEvent):
        if count.value > 0:
            count.value -= 1

    def toggle(ev: DOMEvent):
        opened.value = not opened.value

    return html.DIV(
        {},
        html.H2(
            {},
            "FizzBuzz",
        ),
        html.P(
            {},
            html.BUTTON(
                {"@click": toggle},
                toggle_button_text,
            ),
            html.BUTTON(
                {"@click": add},
                "Add",
            ),
            html.BUTTON(
                {"@click": pop},
                "Pop",
            ),
        ),
        html.P(
            {},
            "Count: ",
            count,
        ),
        switch(
            {
                "case": opened,
                "generator": lambda: FizzbuzzList(props=count),
            },
            default=lambda: html.DIV(
                {},
                "FizzBuzz Hidden",
            ),
        ),
    )
