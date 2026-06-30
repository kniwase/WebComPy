from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext

from ...components.demo_display import DemoDisplay


@define_component
def FizzbuzzPage(context: ComponentContext[RouterContext]):
    context.set_title("FizzBuzz - WebCompy Demo")
    return html.DIV(
        {"class": "page-container"},
        DemoDisplay({"title": "FizzBuzz", "app_name": "fizzbuzz", "demo_path": "/_demos/fizzbuzz/app.py"}),
    )
