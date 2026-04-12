from webcompy.components import (
    TypedComponentBase,
    component_class,
    component_template,
)
from webcompy.elements import html


@component_class
class HelloWorldClassstyle(TypedComponentBase(props_type=None)):
    @component_template
    def template(self):
        return html.DIV(
            {},
            html.H1(
                {},
                "Hello WebComPy!",
            ),
        )
