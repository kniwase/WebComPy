from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.signal import use_reactive_list, use_state


@define_component("repeat-page")
def RepeatPage(context: ComponentContext[None]):
    context.set_title("Repeat - E2E")

    items = use_reactive_list(lambda: [])
    counter = use_state(lambda: 0)

    def add_item(_):
        counter.value += 1
        items.append(f"Item {counter.value}")

    def remove_last(_):
        if len(items.value) > 0:
            items.pop()

    return html.DIV(
        {"data-testid": "repeat-page"},
        html.H2({}, "Repeat Tests"),
        html.BUTTON({"data-testid": "add-btn", "@click": add_item}, "Add"),
        html.BUTTON({"data-testid": "remove-btn", "@click": remove_last}, "Remove Last"),
        html.UL(
            {"data-testid": "item-list"},
            repeat(
                sequence=items,
                template=lambda item: html.LI({"data-testid": "list-item"}, item),
            ),
        ),
    )
