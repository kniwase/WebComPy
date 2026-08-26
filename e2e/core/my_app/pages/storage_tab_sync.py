from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.storage import use_local_storage


@define_component()
def StorageTabSyncPage(context: ComponentContext[None]):
    context.set_title("Storage Tab Sync - E2E")

    synced = use_local_storage("e2e-synced", lambda: "initial", sync_tabs=True)

    def write(_):
        synced.value = "from-button"

    return html.DIV(
        {"data-testid": "storage-tab-sync-page"},
        html.H2({}, "Storage Tab Sync"),
        html.SPAN({"data-testid": "synced-value"}, synced),
        html.BUTTON({"data-testid": "write-btn", "@click": write}, "Write"),
    )
