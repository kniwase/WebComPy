from pathlib import Path
from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from ...components.demo_display import DemoDisplay
from ...templates.demo.helloworld import HelloWorld


@define_component
def HelloWorldPage(context: ComponentContext[RouterContext]):
    title = "HelloWorld"
    context.set_title(f"{title} - WebCompy Demo")
    code = Path(__file__).parents[2] / "templates/demo/helloworld.py"

    return html.DIV(
        {},
        DemoDisplay(
            {
                "title": title,
                "code": code.open().read().strip(),
            },
            slots={"component": lambda: HelloWorld(None)},
        ),
    )
