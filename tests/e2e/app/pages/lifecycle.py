from webcompy.components import (
    TypedComponentBase,
    component_class,
    component_template,
    on_after_rendering,
    on_before_destroy,
    on_before_rendering,
)
from webcompy.elements import html
from webcompy.reactive import Reactive


@component_class
class LifecyclePage(TypedComponentBase(props_type=None)):
    def __init__(self):
        self.count = Reactive(0)
        self.render_count = Reactive(0)

    @on_before_rendering
    def before_render(self):
        pass

    @on_after_rendering
    def after_render(self):
        self.render_count.value += 1

    @on_before_destroy
    def before_destroy(self):
        pass

    def increment(self, _):
        self.count.value += 1

    @component_template
    def template(self):
        return html.DIV(
            {"data-testid": "lifecycle-page"},
            html.H2({}, "Lifecycle Tests"),
            html.P({}, "Count: ", html.SPAN({"data-testid": "lifecycle-count"}, self.count)),
            html.P({}, "Render count: ", html.SPAN({"data-testid": "render-count"}, self.render_count)),
            html.BUTTON({"data-testid": "lifecycle-increment-btn", "@click": self.increment}, "Increment"),
        )
