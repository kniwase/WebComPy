from webcompy.components import (
    TypedComponentBase,
    component_class,
    component_template,
)
from webcompy.elements import html


@component_class
class ClassStylePage(TypedComponentBase(props_type=None)):
    @component_template
    def template(self):
        return html.DIV(
            {"data-testid": "class-style-page"},
            html.H2({}, "Class Style Component"),
            html.P({"data-testid": "class-msg"}, "Hello from class component!"),
        )
