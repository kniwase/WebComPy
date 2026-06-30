from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext

from ...components.demo_display import DemoDisplay


@define_component
def FetchSamplePage(context: ComponentContext[RouterContext]):
    context.set_title("Fetch Sample - WebCompy Demo")
    return html.DIV(
        {"class": "page-container"},
        DemoDisplay(
            {
                "title": "Fetch Sample",
                "app_name": "fetch_sample",
                "demo_path": "/_demos/fetch_sample/app.py",
            }
        ),
    )
