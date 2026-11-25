# WebComPy

[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md)
[![ja](https://img.shields.io/badge/lang-ja-green.svg)](README.ja.md)

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
- **Testing module** — `TestRenderer` and fake ports for browserless component testing — requires `webcompy-testing`
- **Inspector CLI** — Screenshot, console log, DOM query, click, and navigation in headless browser
- **CLI tools** — Project scaffolding (`init`), dev server (`start`), Static Site Generator (`generate`) — requires `webcompy-cli`
- **Type annotations** — Full type hints with `.pyi` stubs

## Get started

### Use in PyScript

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script
    type="module"
    src="https://pyscript.net/releases/2026.3.1/core.js">
  </script>
</head>
<body>
  <py-config>
    packages = ["webcompy"]
  </py-config>
  <py-script>
    from webcompy.signal import Signal
    from webcompy.elements import html
    from webcompy.app import WebComPyApp
    from webcompy.components import define_component, ComponentContext

    @define_component("counter-app")
    def CounterApp(context: ComponentContext[None]):
        count = Signal(0)

        def increment(ev):
            count.value += 1

        return html.DIV(
            {},
            html.P({}, "Count: ", count),
            html.BUTTON({"@click": increment}, "+1"),
        )

    app = WebComPyApp(root_component=CounterApp)
    app.run()
  </py-script>
</body>
</html>
```

Serve the file with any HTTP server and open it in a browser.
No Python installation required on your machine — PyScript runs entirely in the browser.

> **Note**: PyScript resolves `packages` from PyPI and does not yet support installing directly from a GitHub repository. Until the latest release is published to PyPI, the version loaded in PyScript is the last published one. This is a known limitation to be addressed once PyPI releases are in place.

### Develop with the CLI

**uv (recommended)**

```bash
uv init my-project && cd my-project
uv add "webcompy @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy"
uv add "webcompy-server @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-server"
uv add "webcompy-cli @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-cli"
uv run python -m webcompy init       # create project structure
uv run python -m webcompy start --dev # launch dev server with hot-reload
uv run python -m webcompy generate   # build static site
```

**poetry**

```bash
poetry new my-project && cd my-project
poetry add "git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy"
poetry add "git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-server"
poetry add "git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-cli"
poetry run python -m webcompy init   # create project structure
poetry run python -m webcompy start --dev  # launch dev server with hot-reload
poetry run python -m webcompy generate     # build static site
```

**pip**

```bash
mkdir my-project && cd my-project
pip install "webcompy @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy" \
            "webcompy-server @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-server" \
            "webcompy-cli @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-cli"
python -m webcompy init              # create project structure
python -m webcompy start --dev       # launch dev server with hot-reload
python -m webcompy generate          # build static site
```

> **Note**: Until the latest release is published to PyPI, the packages are resolved from the GitHub repository via the URLs above. Once the packages are on PyPI, these can be simplified back to `uv add webcompy-cli` / `poetry add webcompy-cli` / `pip install webcompy[cli]`.

### Testing

```bash
pip install "webcompy @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy" \
            "webcompy-server @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-server" \
            "webcompy-testing @ git+https://github.com/kniwase/WebComPy.git#subdirectory=packages/webcompy-testing"
```

## Documents and Demos
- [webcompy.net](https://webcompy.net/)
    * [Documentation](https://webcompy.net/documents/)
    * [Live Examples](https://webcompy.net/documents/examples/todo)
    * [Source codes](https://github.com/kniwase/WebComPy/tree/main/docs_app/)

## Sample Code
```python
import uuid

from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import DOMEvent, DomNodeRef, html, repeat
from webcompy.signal import Signal, use_computed, use_reactive_dict, use_state


@define_component()
def ToDoItem(context: ComponentContext[dict]):
    input_ref = DomNodeRef()

    def on_change_state(_: DOMEvent):
        context.props["done"].value = input_ref.checked

    return html.LI(
        {},
        html.LABEL(
            {},
            html.INPUT(
                {
                    "type": "checkbox",
                    "@change": on_change_state,
                    ":ref": input_ref,
                },
            ),
        ),
        " ",
        html.SPAN(
            {"style": use_computed(lambda: "text-decoration: line-through;" if context.props["done"].value else "")},
            context.props["title"],
        ),
    )


ToDoItem.scoped_style = {
    "li": {
        "color": "#2d8fdd",
        "border-left": "solid 6px #2d8fdd",
        "background": "#f1f8ff",
        "line-height": "1.5",
        "margin": "5px",
        "padding": "5px",
        "list-style-type": "none",
    }
}


@define_component()
def TodoApp(_: ComponentContext[None]):
    input_ref = DomNodeRef()
    data = use_reactive_dict(
        lambda: {
            str(uuid.uuid4()): {
                "title": use_state(lambda: "Try WebComPy"),
                "done": use_state(lambda: False),
            },
            str(uuid.uuid4()): {
                "title": use_state(lambda: "Create WebComPy project"),
                "done": use_state(lambda: False),
            },
        }
    )

    def append_item(_: DOMEvent):
        title = input_ref.value
        if title:
            data[str(uuid.uuid4())] = {
                "title": Signal(title),
                "done": Signal(False),
            }
        input_ref.value = ""

    def remove_done_items(_: DOMEvent):
        keys_to_remove = [k for k, v in data.value.items() if v["done"].value]
        for k in keys_to_remove:
            del data[k]

    return html.DIV(
        {},
        html.P(
            {},
            "Title: ",
            html.INPUT({":ref": input_ref}),
            html.BUTTON({"@click": append_item}, "Add ToDo"),
            html.BUTTON({"@click": remove_done_items}, "Remove Done Items"),
        ),
        html.UL(
            {},
            repeat(
                data,
                lambda v, k: ToDoItem(v),
            ),
        ),
    )


app = WebComPyApp(root_component=TodoApp)
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow, AI agent usage, and PR process.
For detailed technical reference (commands, invariants, spec mapping), see [AGENTS.md](AGENTS.md).

## License
This project is licensed under the MIT License, see the LICENSE.txt file for details.
