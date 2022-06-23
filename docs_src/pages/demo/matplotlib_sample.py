from pathlib import Path
from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from ...components.demo_display import DemoDisplay
from ...templates.demo.matplotlib_sample import MatpoltlibSample


@define_component
def MatpoltlibSamplePage(context: ComponentContext[RouterContext]):
    title = "Matplotlib Sample"
    context.set_title(f"{title} - WebCompy Demo")
    code = Path(__file__).parents[2] / "templates/demo/matplotlib_sample.py"

    return html.DIV(
        {},
        DemoDisplay(
            {
                "title": title,
                "code": code.open().read().strip(),
            },
            slots={"component": lambda: MatpoltlibSample(None)},
        ),
    )
