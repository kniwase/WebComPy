from typing import TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.reactive import Reactive, ReactiveList


class KeyedItem(TypedDict):
    id: Reactive[str]
    label: Reactive[str]


@define_component
def KeyedRepeatPage(context: ComponentContext[None]):
    context.set_title("Keyed Repeat - E2E")

    items: ReactiveList[KeyedItem] = ReactiveList([])
    counter = Reactive(0)

    def add_item(_):
        counter.value += 1
        c = counter.value
        items.append({"id": Reactive(f"id-{c}"), "label": Reactive(f"Item {c}")})

    def add_at_start(_):
        counter.value += 1
        c = counter.value
        items.insert(0, {"id": Reactive(f"id-{c}"), "label": Reactive(f"Item {c}")})

    def add_at_middle(_):
        counter.value += 1
        c = counter.value
        idx = len(items.value) // 2
        items.insert(idx, {"id": Reactive(f"id-{c}"), "label": Reactive(f"Item {c}")})

    def remove_first(_):
        if len(items.value) > 0:
            items.pop(0)

    def remove_last(_):
        if len(items.value) > 0:
            items.pop()

    def reverse_items(_):
        items.reverse()

    return html.DIV(
        {"data-testid": "keyed-repeat-page"},
        html.H2({}, "Keyed Repeat Tests"),
        html.BUTTON({"data-testid": "keyed-add-btn", "@click": add_item}, "Add"),
        html.BUTTON({"data-testid": "keyed-add-start-btn", "@click": add_at_start}, "Add at Start"),
        html.BUTTON({"data-testid": "keyed-add-middle-btn", "@click": add_at_middle}, "Add at Middle"),
        html.BUTTON({"data-testid": "keyed-remove-first-btn", "@click": remove_first}, "Remove First"),
        html.BUTTON({"data-testid": "keyed-remove-last-btn", "@click": remove_last}, "Remove Last"),
        html.BUTTON({"data-testid": "keyed-reverse-btn", "@click": reverse_items}, "Reverse"),
        html.UL(
            {"data-testid": "keyed-item-list"},
            repeat(
                sequence=items,
                template=lambda item, k: html.LI(
                    {"data-testid": "keyed-list-item", "data-key": item["id"]},
                    item["label"],
                    html.INPUT({"data-testid": "keyed-input", "value": item["label"]}),
                ),
                key=lambda item: item["id"].value,
            ),
        ),
    )
