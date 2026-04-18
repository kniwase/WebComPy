from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import ReactiveDict, ReactiveList, Signal, computed


@define_component
def ReactivePage(context: ComponentContext[None]):
    context.set_title("Signal - E2E")

    count = Signal(0)
    doubled = computed(lambda: count.value * 2)
    items = ReactiveList([1, 2, 3])
    rdict = ReactiveDict({"key1": "val1"})
    item_count = computed(lambda: str(len(items.value)))
    dict_count = computed(lambda: str(len(rdict.value)))

    def increment(_):
        count.value += 1

    def decrement(_):
        count.value -= 1

    def add_item(_):
        items.append(len(items.value) + 1)

    def remove_item(_):
        if len(items.value) > 0:
            items.pop()

    def add_dict_key(_):
        rdict.value = {**rdict.value, f"key{len(rdict.value) + 1}": f"val{len(rdict.value) + 1}"}

    return html.DIV(
        {"data-testid": "reactive-page"},
        html.H2({}, "Signal Tests"),
        html.DIV(
            {},
            html.SPAN({"data-testid": "count"}, count),
            html.SPAN({"data-testid": "doubled"}, doubled),
            html.BUTTON({"data-testid": "increment-btn", "@click": increment}, "Add"),
            html.BUTTON({"data-testid": "decrement-btn", "@click": decrement}, "Sub"),
        ),
        html.DIV(
            {},
            html.SPAN({"data-testid": "list-count"}, item_count),
            html.BUTTON({"data-testid": "list-add-btn", "@click": add_item}, "Add Item"),
            html.BUTTON({"data-testid": "list-remove-btn", "@click": remove_item}, "Remove Item"),
        ),
        html.DIV(
            {},
            html.SPAN({"data-testid": "dict-count"}, dict_count),
            html.BUTTON({"data-testid": "dict-add-btn", "@click": add_dict_key}, "Add Key"),
        ),
    )
