from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext

from ...components.demo_display import DemoDisplay


@define_component
def HelloWorldPage(context: ComponentContext[RouterContext]):
    context.set_title("HelloWorld - WebCompy Demo")
    return html.DIV(
        {"class": "container"},
        DemoDisplay(
            {"title": "HelloWorld", "app_name": "helloworld", "demo_path": "/_demos/helloworld/app.py", "packages": []}
        ),
    )
