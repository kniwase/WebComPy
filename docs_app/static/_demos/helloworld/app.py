from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component("hello-world-app")
def HelloWorld(_: ComponentContext[None]):
    return html.DIV(
        {},
        html.H1(
            {},
            "Hello WebComPy!",
        ),
    )


app = WebComPyApp(root_component=HelloWorld)
app.run()
