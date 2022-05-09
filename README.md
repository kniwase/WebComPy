# WebComPy

## What is WebComPy
[WebComPy](https://github.com/kniwase/WebComPy) is Python frontend framework on Browser (powered by [Brython](https://github.com/brython-dev/brython), thank you very much!), which has following features.

- Component-based declarative rendering
- Automatic DOM refreshing
- Built-in router
- Built-in server / Static Site Generation

## Get started
```
mkdir webcompy-project
cd webcompy-project
pip install webcompy
python -m webcompy init
python -m webcompy start --dev
```

then access [http://127.0.0.1:8080/WebComPy/](http://127.0.0.1:8080/WebComPy/)

## Documents and Demos
- [Github Pages](https://kniwase.github.io/WebComPy/)
    * [Source Codes](https://github.com/kniwase/WebComPy/tree/main/docs_src/)
    * [Generated Files](https://github.com/kniwase/WebComPy/tree/main/docs/)

## Sample Code
```python
from webcompy.reactive import Reactive, computed_property, computed
from webcompy.elements import html, repeat, switch, DOMEvent
from webcompy.router import RouterContext
from webcompy.components import (
    define_component,
    ComponentContext,
    TypedComponentBase,
    component_class,
    on_before_rendering,
    component_template,
)


@define_component
def FizzbuzzList(context: ComponentContext[Reactive[int]]):
    @computed
    def fizzbuzz():
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
            repeat(fizzbuzz, lambda s: html.LI({}, s)),
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
            html.H3(
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
                default=lambda: html.H5(
                    {},
                    "FizzBuzz Hidden",
                ),
            ),
        )

```

## ToDo
- Add PyScript support ([Github Repo](https://github.com/pyscript/pyscript))
- Add provide/inject (DI)
- Add Plugin System

## Lisence
This project is licensed under the MIT License, see the LICENSE.txt file for details.
