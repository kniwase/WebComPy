from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from ...components.demo_display import DemoDisplay
from ...templates.demo.helloworld_classstyle import HelloWorldClassstyle


@define_component
def HelloWorldClassstylePage(context: ComponentContext[RouterContext]):
    title = "HelloWorld (ClassStyle)"
    context.set_title(f"{title} - WebCompy Demo")

    return html.DIV(
        {},
        DemoDisplay(
            {
                "title": title,
                "code": """
                    from webcompy.elements import html
                    from webcompy.components import (
                        TypedComponentBase,
                        component_class,
                        component_template,
                    )


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
                            )""",
            },
            slots={"component": lambda: HelloWorldClassstyle(None)},
        ),
    )
