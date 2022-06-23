from pathlib import Path
from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from ...components.demo_display import DemoDisplay
from ...templates.demo.helloworld_classstyle import HelloWorldClassstyle


@define_component
def HelloWorldClassstylePage(context: ComponentContext[RouterContext]):
    title = "HelloWorld (ClassStyle)"
    context.set_title(f"{title} - WebCompy Demo")
    code = Path(__file__).parents[2] / "templates/demo/helloworld_classstyle.py"

    return html.DIV(
        {},
        DemoDisplay(
            {
                "title": title,
                "code": code.open().read().strip(),
            },
            slots={"component": lambda: HelloWorldClassstyle(None)},
        ),
    )
