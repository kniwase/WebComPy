from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext

from ...components.demo_display import DemoDisplay


@define_component
def MatplotlibSamplePage(context: ComponentContext[RouterContext]):
    context.set_title("Matplotlib Sample - WebCompy Demo")
    return html.DIV(
        {"class": "page-container"},
        DemoDisplay(
            {
                "title": "Matplotlib Sample",
                "app_name": "matplotlib_sample",
                "demo_path": "/_demos/matplotlib_sample/app.py",
            }
        ),
    )
