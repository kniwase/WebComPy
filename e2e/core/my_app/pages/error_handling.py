from webcompy.components import ComponentContext, define_component
from webcompy.elements import ErrorBoundary, html
from webcompy.elements.generators import repeat
from webcompy.router import RouterContext
from webcompy.signal import use_reactive_list


@define_component
def RiskyWidget(context: ComponentContext[None]):
    items = use_reactive_list(lambda: ["a"])

    def add_bad(_):
        items.append("bad")

    def render_item(v: str):
        if v == "bad":
            raise RuntimeError("widget render failed")
        return html.LI({"data-testid": f"risky-item-{v}"}, v)

    return html.DIV(
        {"data-testid": "risky-widget"},
        html.BUTTON({"data-testid": "crash-widget", "@click": add_bad}, "Crash widget"),
        html.UL({}, repeat(items, render_item)),
    )


@define_component
def ErrorBoundaryPage(context: ComponentContext[RouterContext]):
    def fallback(error: Exception, reset):
        return html.DIV(
            {"data-testid": "eb-fallback"},
            html.P({"data-testid": "eb-error"}, str(error)),
            html.BUTTON({"data-testid": "eb-retry", "@click": lambda _: reset()}, "Retry"),
        )

    return html.DIV(
        {"data-testid": "eb-page"},
        ErrorBoundary(children=lambda: RiskyWidget(None), fallback=fallback),
        html.SPAN({"data-testid": "eb-sibling"}, "alive"),
    )


@define_component
def NestedCrashPage(context: ComponentContext[RouterContext]):
    items = use_reactive_list(lambda: ["a"])

    def add_bad(_):
        items.append("bad")

    def render_item(v: str):
        if v == "bad":
            raise RuntimeError("page render failed")
        return html.LI({"data-testid": f"crash-item-{v}"}, v)

    return html.DIV(
        {"data-testid": "nested-crash-page"},
        html.BUTTON({"data-testid": "crash-page", "@click": add_bad}, "Crash page"),
        html.UL({}, repeat(items, render_item)),
    )


@define_component
def CatchEventsPage(context: ComponentContext[RouterContext]):
    def fallback(error: Exception, reset):
        return html.DIV(
            {"data-testid": "ce-fallback"},
            html.P({"data-testid": "ce-error"}, str(error)),
            html.BUTTON({"data-testid": "ce-retry", "@click": lambda _: reset()}, "Retry"),
        )

    def raise_in_handler(_):
        raise RuntimeError("event handler failed")

    return html.DIV(
        {"data-testid": "ce-page"},
        ErrorBoundary(
            children=lambda: html.BUTTON(
                {"data-testid": "ce-crash", "@click": raise_in_handler},
                "Raise in handler",
            ),
            fallback=fallback,
            catch_events=True,
        ),
        html.SPAN({"data-testid": "ce-sibling"}, "alive"),
    )
