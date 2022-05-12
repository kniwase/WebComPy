from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from ...components.demo_display import DemoDisplay
from ...templates.demo.helloworld import HelloWorld


@define_component
def HelloWorldPage(context: ComponentContext[RouterContext]):
    title = "HelloWorld"
    context.set_title(f"{title} - WebCompy Demo")

    return html.DIV(
        {},
        DemoDisplay(
            {
                "title": title,
                "code": """
                    from webcompy.elements import html
                    from webcompy.components import define_component, ComponentContext


                    @define_component
                    def HelloWorld(_: ComponentContext[None]):
                        return html.DIV(
                            {},
                            html.H1(
                                {},
                                "Hello WebComPy!",
                            ),
                        )""",
            },
            slots={"component": lambda: HelloWorld(None)},
        ),
    )
