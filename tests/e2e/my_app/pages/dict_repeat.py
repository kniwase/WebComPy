from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.signal import ReactiveDict, Signal


@define_component
def DictRepeatPage(context: ComponentContext[None]):
    context.set_title("Dict Repeat - E2E")

    data: ReactiveDict[str, str] = ReactiveDict()
    counter = Signal(0)

    def add_item(_):
        counter.value += 1
        c = counter.value
        data[f"key-{c}"] = f"Value {c}"

    def remove_first(_):
        if len(data.value) > 0:
            first_key = next(iter(data.value))
            del data[first_key]

    def clear_all(_):
        data.clear()

    return html.DIV(
        {"data-testid": "dict-repeat-page"},
        html.H2({}, "Dict Repeat Tests"),
        html.BUTTON({"data-testid": "dict-add-btn", "@click": add_item}, "Add"),
        html.BUTTON({"data-testid": "dict-remove-first-btn", "@click": remove_first}, "Remove First"),
        html.BUTTON({"data-testid": "dict-clear-btn", "@click": clear_all}, "Clear"),
        html.UL(
            {"data-testid": "dict-item-list"},
            repeat(
                data,
                lambda v, k: html.LI(
                    {"data-testid": "dict-list-item", "data-key": k},
                    v,
                    html.INPUT({"data-testid": "dict-input", "value": v}),
                ),
            ),
        ),
    )
