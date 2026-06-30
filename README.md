# WebComPy

## What is WebComPy
[WebComPy](https://github.com/kniwase/WebComPy) is a Python frontend framework for [PyScript](https://github.com/pyscript/pyscript). It brings a reactive component model to the browser — entirely in Python.

### Features

- **Component-based declarative rendering** — Define UI components as pure Python functions with `@define_component`
- **Reactive state management** — `Signal`, `Computed`, `ReactiveList`, `ReactiveDict` with automatic DOM diffing
- **Built-in router** — History and hash mode routing with path parameters
- **Dependency Injection** — `provide()` / `inject()` pattern for scoped services
- **Async rendering pipeline** — `async` lifecycle hooks, `AsyncResult`, composable async data fetching
- **HTTP Client** — Browser-native fetch wrapper with async/await
- **Plugin system** — Extend apps via `WebComPyPlugin` base class
- **UI Toolkit** — Theme system (light/dark), `CodeBlock` component, CSS design tokens
- **Testing module** — `TestRenderer` and fake ports for browserless component testing
- **Inspector CLI** — Screenshot, console log, DOM query, click, and navigation in headless browser
- **CLI tools** — Project scaffolding (`init`), dev server (`start`), Static Site Generator (`generate`)
- **Type annotations** — Full type hints with `.pyi` stubs

## Get started

### uv (recommended)
```
uv init my-project && cd my-project
uv add webcompy
uv run python -m webcompy init
uv run python -m webcompy start --dev
```

### poetry
```
poetry new my-project && cd my-project
poetry add webcompy
poetry run python -m webcompy init
poetry run python -m webcompy start --dev
```

### pip
```
pip install webcompy
webcompy init my-project
cd my-project
webcompy start --dev
```

> Note: `uv init` creates a stub `hello.py` that can be deleted after running `webcompy init`.

then access [http://127.0.0.1:8080/](http://127.0.0.1:8080/)

For static site generation:

```
webcompy generate
```

## Documents and Demos
- [webcompy.net](https://webcompy.net/)
    * [Source codes](https://github.com/kniwase/WebComPy/tree/main/docs_app/)

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow, AI agent usage, and PR process.
For detailed technical reference (commands, invariants, spec mapping), see [AGENTS.md](AGENTS.md).

## License
This project is licensed under the MIT License, see the LICENSE.txt file for details.
