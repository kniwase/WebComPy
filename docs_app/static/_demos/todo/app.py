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
        "color": "var(--color-fg)",
        "border": "1px solid var(--color-border)",
        "border-left": "6px solid var(--color-accent)",
        "background": "var(--color-bg-card)",
        "border-radius": "var(--radius-sm)",
        "line-height": "1.5",
        "margin": "var(--space-2) 0",
        "padding": "var(--space-2) var(--space-3)",
        "vertical-align": "middle",
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
        {"class": "todo-demo"},
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


TodoApp.scoped_style = {
    ".todo-demo": {
        "padding": "var(--space-3)",
        "color": "var(--color-fg)",
    },
    ".todo-demo p": {
        "display": "flex",
        "flex-wrap": "wrap",
        "align-items": "center",
        "gap": "var(--space-2)",
        "margin": "0 0 var(--space-3) 0",
    },
    ".todo-demo input": {
        "padding": "0.35rem 0.5rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg)",
        "color": "var(--color-fg)",
    },
    ".todo-demo ul": {
        "padding": "0",
        "margin": "0",
    },
    "button": {
        "display": "inline-block",
        "text-decoration": "none",
        "padding": "0.35rem 0.75rem",
        "border": "1px solid var(--color-accent)",
        "border-radius": "var(--radius-sm)",
        "transition": "background-color 0.15s ease, color 0.15s ease",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
        "cursor": "pointer",
    },
    "button:hover": {
        "background": "var(--color-accent)",
        "color": "var(--color-on-accent)",
    },
}

app = WebComPyApp(root_component=TodoApp)
app.run()
