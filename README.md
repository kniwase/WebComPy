# WebComPy

Python client-side web framework

## ToDo
- Add PyScript support ([Github Repo](https://github.com/pyscript/pyscript))
- Add CLI tool
- Add provide/inject (DI)
- Add JavaScript/CSS libraries loader
- Add Plugin System

## Sample Code
```python
from webcompy.app import WebComPyApp
from webcompy.brython import DOMEvent
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, event, repeat
from webcompy.reactive import Reactive, computed


@define_component
def FizzbuzzCore(context: ComponentContext[Reactive[int]]):
    @computed
    def numbers():
        return [
            "FizzBuzz"
            if n % 15 == 0
            else "Fizz"
            if n % 5 == 0
            else "Buzz"
            if n % 3 == 0
            else str(n)
            for n in map(lambda n: n + 1, range(context.props.value))
        ]

    return html.UL(
        {},
        repeat(
            numbers,
            lambda s: html.LI({}, s),
        ),
    )


FizzbuzzCore.scoped_style = {
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
def Fizzbuzz(context: ComponentContext[None]):
    count = Reactive(10)

    def add(ev: DOMEvent):
        count.value += 1

    def pop(ev: DOMEvent):
        if count.value:
            count.value -= 1

    @context.on_before_rendering
    def _():
        count.value = 10

    return html.DIV(
        {},
        html.H1({}, "FizzBuzz"),
        html.P(
            {},
            html.BUTTON({event("click"): add}, "Add"),
            html.BUTTON({event("click"): pop}, "Pop"),
        ),
        FizzbuzzCore(
            props=count,
        ),
    )


app = WebComPyApp(root_component=Fizzbuzz)
app.init()
```
