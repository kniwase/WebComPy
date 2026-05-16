from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext

from ...components.demo_display import DemoDisplay


@define_component
def ToDoListPage(context: ComponentContext[RouterContext]):
    context.set_title("ToDo List - WebCompy Demo")
    return html.DIV(
        {"class": "container"},
        DemoDisplay({"title": "ToDo List", "app_name": "todo", "demo_path": "/_demos/todo/app.py"}),
    )
