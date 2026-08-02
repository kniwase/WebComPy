from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext, RouterLink, RouterView
from webcompy.signal import use_computed, use_state

_guide_setup_count = 0
_api_setup_count = 0
_item_setup_count = 0


@define_component
def NestedDocsLayout(context: ComponentContext[RouterContext]):
    sidebar_open = use_state(lambda: True)
    sidebar_label = use_computed(lambda: "open" if sidebar_open.value else "closed")
    tab_b_query = use_state(lambda: {"tab": "b"})

    def toggle(_):
        sidebar_open.value = not sidebar_open.value

    return html.DIV(
        {"data-testid": "nested-layout"},
        html.NAV(
            {},
            html.UL(
                {},
                html.LI({}, RouterLink(to="/nested", text=["Index"], attrs={"data-testid": "nav-nested-index"})),
                html.LI({}, RouterLink(to="/nested/guide", text=["Guide"], attrs={"data-testid": "nav-nested-guide"})),
                html.LI(
                    {},
                    RouterLink(
                        to="/nested/guide",
                        text=["Guide?tab=b"],
                        query=tab_b_query,
                        attrs={"data-testid": "nav-guide-tab-b"},
                    ),
                ),
                html.LI({}, RouterLink(to="/nested/api", text=["API"], attrs={"data-testid": "nav-nested-api"})),
                html.LI(
                    {}, RouterLink(to="/nested/item/1", text=["Item 1"], attrs={"data-testid": "nav-nested-item1"})
                ),
                html.LI(
                    {}, RouterLink(to="/nested/item/2", text=["Item 2"], attrs={"data-testid": "nav-nested-item2"})
                ),
            ),
        ),
        html.BUTTON({"data-testid": "nested-toggle", "@click": toggle}, "Toggle Sidebar"),
        html.SPAN({"data-testid": "nested-sidebar"}, sidebar_label),
        html.MAIN({}, RouterView()),
    )


@define_component
def NestedDocsIndexPage(context: ComponentContext[RouterContext]):
    return html.DIV({"data-testid": "nested-index-page"}, html.H1({}, "Nested Index"))


@define_component
def NestedDocsGuidePage(context: ComponentContext[RouterContext]):
    global _guide_setup_count
    _guide_setup_count += 1
    return html.DIV(
        {"data-testid": "nested-guide-page"},
        html.H1({}, "Nested Guide"),
        html.SPAN({"data-testid": "nested-guide-count"}, str(_guide_setup_count)),
    )


@define_component
def NestedDocsApiPage(context: ComponentContext[RouterContext]):
    global _api_setup_count
    _api_setup_count += 1
    return html.DIV(
        {"data-testid": "nested-api-page"},
        html.H1({}, "Nested API"),
        html.SPAN({"data-testid": "nested-api-count"}, str(_api_setup_count)),
    )


@define_component
def NestedDocsItemPage(context: ComponentContext[RouterContext]):
    global _item_setup_count
    _item_setup_count += 1
    return html.DIV(
        {"data-testid": "nested-item-page"},
        html.H1({}, "Nested Item"),
        html.SPAN({"data-testid": "nested-item-id"}, str(context.props.path_params.get("id"))),
        html.SPAN({"data-testid": "nested-item-count"}, str(_item_setup_count)),
    )
