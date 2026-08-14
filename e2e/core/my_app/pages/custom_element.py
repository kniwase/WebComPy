from webcompy.components import (
    ComponentContext,
    define_component,
    on_mounted,
    on_unmounted,
    reactive_scoped_style,
)
from webcompy.elements import html, repeat, switch
from webcompy.signal import use_computed, use_reactive_list, use_state


@define_component("e2e-card", observed_attributes=("theme-color",))
def E2ECard(context: ComponentContext[dict]):
    theme = use_computed(lambda: context.props["theme_color"] or "none")

    @on_mounted
    def mounted():
        context.props["mounted_total"].value += 1

    @on_unmounted
    def unmounted():
        context.props["unmounted_total"].value += 1

    context.use_reactive_scoped_style(reactive_scoped_style(lambda: {":host": {"color": "blue", "display": "block"}}))

    return [
        html.HEADER({}, html.SPAN({"data-testid": "card-theme"}, theme)),
        html.MAIN({"data-testid": "card-body"}, "body"),
        html.FOOTER({}, "footer"),
    ]


@define_component
def CustomElementPage(context: ComponentContext[None]):
    context.set_title("Custom Elements - E2E")

    mounted_total = use_state(lambda: 0)
    unmounted_total = use_state(lambda: 0)
    items = use_reactive_list(lambda: [{"id": "a"}, {"id": "b"}])

    def add_item(_):
        items.append({"id": f"x{len(items.value)}"})

    def remove_first(_):
        if items.value:
            items.pop(0)

    def reverse_items(_):
        items.reverse()

    adopt_on = use_state(lambda: True)

    def toggle_adopt(_):
        adopt_on.value = not adopt_on.value

    def adopt_card():
        return E2ECard(
            {
                "id": "adopt",
                "mounted_total": mounted_total,
                "unmounted_total": unmounted_total,
            }
        )

    return html.DIV(
        {"data-testid": "custom-element-page"},
        html.H2({}, "Custom Element Tests"),
        html.P({}, "Mounted: ", html.SPAN({"data-testid": "mounted-total"}, mounted_total)),
        html.P({}, "Unmounted: ", html.SPAN({"data-testid": "unmounted-total"}, unmounted_total)),
        html.BUTTON({"data-testid": "add-btn", "@click": add_item}, "Add"),
        html.BUTTON({"data-testid": "remove-btn", "@click": remove_first}, "Remove First"),
        html.BUTTON({"data-testid": "reverse-btn", "@click": reverse_items}, "Reverse"),
        html.DIV(
            {"data-testid": "card-list"},
            repeat(
                items,
                lambda item, k: E2ECard(
                    {
                        "id": item["id"],
                        "mounted_total": mounted_total,
                        "unmounted_total": unmounted_total,
                    }
                ),
                key=lambda item: item["id"],
            ),
        ),
        html.H2({}, "Adoption Switch"),
        html.BUTTON({"data-testid": "adopt-toggle-btn", "@click": toggle_adopt}, "Flip"),
        html.DIV(
            {"data-testid": "adopt-area"},
            switch(
                {
                    "case": adopt_on,
                    "generator": adopt_card,
                },
                default=adopt_card,
            ),
        ),
    )
