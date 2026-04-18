from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
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
                    from webcompy.components import define_component, ComponentContext


                    @define_component
                    def HelloWorldClassstyle(_: ComponentContext[None]):
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
