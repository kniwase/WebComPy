from webcompy.components import (
    ComponentContext,
    define_component,
    on_after_rendering,
    on_before_destroy,
    on_before_rendering,
)
from webcompy.elements import html
from webcompy.signal import Signal


@define_component
def LifecyclePage(context: ComponentContext[None]):
    context.set_title("Lifecycle - E2E")

    count = Signal(0)
    render_count = Signal(0)

    @on_before_rendering
    def before_render():
        pass

    @on_after_rendering
    def after_render():
        render_count.value += 1

    @on_before_destroy
    def before_destroy():
        pass

    def increment(_):
        count.value += 1

    return html.DIV(
        {"data-testid": "lifecycle-page"},
        html.H2({}, "Lifecycle Tests"),
        html.P({}, "Count: ", html.SPAN({"data-testid": "lifecycle-count"}, count)),
        html.P({}, "Render count: ", html.SPAN({"data-testid": "render-count"}, render_count)),
        html.BUTTON({"data-testid": "lifecycle-increment-btn", "@click": increment}, "Increment"),
    )
