from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat, switch
from webcompy.reactive import Reactive, ReactiveList, computed


@define_component
def NestedDynamicPage(context: ComponentContext[None]):
    context.set_title("Nested Dynamic - E2E")

    view_mode = Reactive("list")
    items = ReactiveList(["Alpha", "Beta", "Gamma"])
    counter = Reactive(0)

    is_list = computed(lambda: view_mode.value == "list")
    is_grid = computed(lambda: view_mode.value == "grid")

    def set_list(_):
        view_mode.value = "list"

    def set_grid(_):
        view_mode.value = "grid"

    def add_item(_):
        counter.value += 1
        items.append(f"Item-{counter.value}")

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
            html.BUTTON({"data-testid": "add-item-btn", "@click": add_item}, "Add"),
            html.BUTTON({"data-testid": "remove-first-btn", "@click": remove_first}, "Remove First"),
        ),
        html.DIV(
            {"data-testid": "nested-container"},
            switch(
                {
                    "case": is_list,
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
                    "case": is_grid,
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
