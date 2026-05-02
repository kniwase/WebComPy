# WebComPy

## What is WebComPy
[WebComPy](https://github.com/kniwase/WebComPy) is Python frontend framework for [PyScript](https://github.com/pyscript/pyscript), which has following features.

- Component-based declarative rendering
- Automatic DOM refreshing
- Built-in router
- CLI tool (Project template, Build-in HTTP server, Static Site Generator)
- Type Annotation

## Get started
```
uv init webcompy-project        # create a new project directory
cd webcompy-project
uv add webcompy                 # install webcompy from PyPI
uv run python -m webcompy init  # scaffold WebComPy project files
uv run python -m webcompy start --dev
uv run python -m webcompy generate  # for generating static site
```

> Note: `uv init` creates a stub `hello.py` that can be deleted after running `webcompy init`.

then access [http://127.0.0.1:8080/](http://127.0.0.1:8080/)

## Documents and Demos
- [webcompy.net](https://webcompy.net/)
    * [Source Codes](https://github.com/kniwase/WebComPy/tree/main/docs_app/)
    * [Generated Files](https://github.com/kniwase/WebComPy/tree/main/docs/)

## Sample Code
```python
from webcompy.signal import Signal, computed
from webcompy.elements import html, repeat, switch, DOMEvent
from webcompy.router import RouterContext
from webcompy.components import (
    define_component,
    ComponentContext,
    on_before_rendering,
)


@define_component
def FizzbuzzList(context: ComponentContext[Signal[int]]):
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


@define_component
def Fizzbuzz(context: ComponentContext[RouterContext]):
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
        html.H3(
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
            default=lambda: html.H5(
                {},
                "FizzBuzz Hidden",
            ),
        ),
    )

```

## Contributing

See [AGENTS.md](AGENTS.md) for development setup, tooling, and coding conventions.

## ToDo
- Add Plugin System
- UI Skeleton Components (layout, navigation, and responsive scaffolding utilities)
- RPC Support (browser-to-server remote procedure calls via PyScript)
- Cloudflare Deployment (static site + Python Workers for RPC)
- PWA Support (offline-capable mobile apps built entirely in Python)

## License
This project is licensed under the MIT License, see the LICENSE.txt file for details.
