from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import use_reactive_list
from webcompy.template import render_markdown


@define_component()
def MarkdownForPage(context: ComponentContext[None]):
    context.set_title("Markdown For - E2E")

    items = use_reactive_list(lambda: ["alpha", "beta"])

    return html.DIV(
        {"data-testid": "markdown-for-page"},
        html.H2({}, "Markdown For Tests"),
        render_markdown(
            "{% for item in items %}\n- {{ item }}\n{% endfor %}",
            {"items": items},
        ),
        html.BUTTON(
            {"data-testid": "add-item", "@click": lambda _: items.append("gamma")},
            "Add Item",
        ),
    )
