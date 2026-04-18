from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterLink, RouterView


@define_component
def Root(_: ComponentContext[None]):
    return html.DIV(
        {},
        html.NAV(
            {"data-testid": "nav"},
            html.UL(
                {},
                html.LI({}, RouterLink(to="/", text=["Home"], attrs={"data-testid": "nav-home"})),
                html.LI({}, RouterLink(to="/reactive", text=["Signal"], attrs={"data-testid": "nav-reactive"})),
                html.LI({}, RouterLink(to="/component", text=["Component"], attrs={"data-testid": "nav-component"})),
                html.LI({}, RouterLink(to="/event", text=["Event"], attrs={"data-testid": "nav-event"})),
                html.LI({}, RouterLink(to="/switch", text=["Switch"], attrs={"data-testid": "nav-switch"})),
                html.LI({}, RouterLink(to="/repeat", text=["Repeat"], attrs={"data-testid": "nav-repeat"})),
                html.LI({}, RouterLink(to="/lifecycle", text=["Lifecycle"], attrs={"data-testid": "nav-lifecycle"})),
                html.LI(
                    {}, RouterLink(to="/scoped-style", text=["ScopedStyle"], attrs={"data-testid": "nav-scoped-style"})
                ),
                html.LI({}, RouterLink(to="/async-nav", text=["AsyncNav"], attrs={"data-testid": "nav-async-nav"})),
            ),
        ),
        html.MAIN(
            {},
            html.ARTICLE(
                {},
                RouterView(),
            ),
        ),
    )
