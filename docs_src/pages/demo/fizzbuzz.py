from pathlib import Path
from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from ...templates.demo.fizzbuzz import Fizzbuzz
from ...components.demo_display import DemoDisplay


@define_component
def FizzbuzzPage(context: ComponentContext[RouterContext]):
    title = "FizzBuzz"
    context.set_title(f"{title} - WebCompy Demo")
    code = Path(__file__).parents[2] / "templates/demo/fizzbuzz.py"

    return html.DIV(
        {},
        DemoDisplay(
            {
                "title": title,
                "code": code.open().read().strip(),
            },
            slots={"component": lambda: Fizzbuzz(None)},
        ),
    )
