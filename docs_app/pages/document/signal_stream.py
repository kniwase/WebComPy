from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext

from ...templates.document.signal_stream import SignalStream


@define_component
def SignalStreamPage(context: ComponentContext[RouterContext]):
    context.set_title("Signal Stream - WebComPy")

    return html.DIV({}, SignalStream(None))
