from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat, switch
from webcompy.reactive import Reactive, ReactiveList


@define_component
def NestedDynamicPage(context: ComponentContext[None]):
    context.set_title("Nested Dynamic - E2E")

    view_mode = Reactive("list")
    items = ReactiveList(["Alpha", "Beta", "Gamma"])
    new_item = Reactive("")

    def set_list(_):
        view_mode.value = "list"

    def set_grid(_):
        view_mode.value = "grid"

    def add_item(_):
        if new_item.value:
            items.append(new_item.value)
            new_item.value = ""

    def remove_first(_):
        if len(items.value) > 0:
            items.pop(0)

    return html.DIV(
        {"data-testid": "nested-dynamic-page"},
        html.H2({}, "Nested Dynamic Tests"),
        html.DIV(
            {"data-testid": "view-controls"},
            html.BUTTON({"data-testid": "list-btn", "@click": set_list}, "List View"),
            html.BUTTON({"data-testid": "grid-btn", "@click": set_grid}, "Grid View"),
        ),
        html.DIV(
            {"data-testid": "add-controls"},
            html.INPUT({"data-testid": "new-item-input", "value": new_item}),
            html.BUTTON({"data-testid": "add-item-btn", "@click": add_item}, "Add"),
            html.BUTTON({"data-testid": "remove-first-btn", "@click": remove_first}, "Remove First"),
        ),
        html.DIV(
            {"data-testid": "nested-container"},
            switch(
                {
                    "case": Reactive(lambda: view_mode.value == "list"),
                    "generator": lambda: html.UL(
                        {"data-testid": "list-view"},
                        repeat(
                            sequence=items,
                            template=lambda item: html.LI(
                                {"data-testid": "list-item"},
                                item,
                            ),
                        ),
                    ),
                },
                {
                    "case": Reactive(lambda: view_mode.value == "grid"),
                    "generator": lambda: html.DIV(
                        {"data-testid": "grid-view"},
                        repeat(
                            sequence=items,
                            template=lambda item: html.SPAN(
                                {"data-testid": "grid-item"},
                                item,
                            ),
                        ),
                    ),
                },
            ),
        ),
    )
