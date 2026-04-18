from typing import TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.signal import ReactiveList, Signal


class ItemData(TypedDict):
    name: Signal[str]


@define_component
def RepeatPage(context: ComponentContext[None]):
    context.set_title("Repeat - E2E")

    items: ReactiveList[ItemData] = ReactiveList([])
    counter = Signal(0)

    def add_item(_):
        counter.value += 1
        items.append({"name": Signal(f"Item {counter.value}")})

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
                template=lambda item: html.LI({"data-testid": "list-item"}, item["name"]),
            ),
        ),
    )
