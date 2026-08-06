from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.storage import use_local_storage, use_session_storage


@define_component
def StoragePage(context: ComponentContext[None]):
    context.set_title("Storage - E2E")

    theme = use_local_storage("e2e-theme", lambda: "light")
    draft = use_session_storage("e2e-draft", lambda: "")

    def set_dark(_):
        theme.value = "dark"

    def set_draft(_):
        draft.value = "hello"

    return html.DIV(
        {"data-testid": "storage-page"},
        html.H2({}, "Storage Tests"),
        html.SPAN({"data-testid": "theme"}, theme),
        html.BUTTON({"data-testid": "theme-dark-btn", "@click": set_dark}, "Dark"),
        html.SPAN({"data-testid": "draft"}, draft),
        html.BUTTON({"data-testid": "draft-btn", "@click": set_draft}, "Set Draft"),
    )
