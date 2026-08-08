from webcompy.components import ComponentContext, define_component, on_before_destroy
from webcompy.elements import html, repeat
from webcompy.signal import use_reactive_list, use_state
from webcompy.utils._environment import ENVIRONMENT


def _format_field(value: object, ffi) -> str:
    if value is None:
        return "<null>"
    if ffi.is_none(value):
        return "<null>"
    return str(value)


@define_component
def StorageSyncSpikePage(context: ComponentContext[None]):
    context.set_title("Storage Sync Spike - E2E")

    records = use_reactive_list(lambda: [])
    status = use_state(lambda: "attached")

    if ENVIRONMENT == "pyscript":
        from pyscript import context as pyscript_context
        from pyscript import ffi as pyscript_ffi

        window = pyscript_context.window

        def _on_storage(event):
            records.append(
                f"key={_format_field(event.key, pyscript_ffi)}|newValue={_format_field(event.newValue, pyscript_ffi)}|url={_format_field(event.url, pyscript_ffi)}"
            )

        proxy = pyscript_ffi.create_proxy(_on_storage)
        window.addEventListener("storage", proxy)

        def detach(_):
            window.removeEventListener("storage", proxy)
            proxy.destroy()
            status.value = "detached"

        def write_py(_):
            window.localStorage.setItem("spike-key", '"python-write"')

        @on_before_destroy
        def cleanup():
            window.removeEventListener("storage", proxy)
            proxy.destroy()
    else:

        def detach(_):
            pass

        def write_py(_):
            pass

    return html.DIV(
        {"data-testid": "storage-sync-spike-page"},
        html.H2({}, "Storage Sync Spike"),
        html.P({"data-testid": "detach-state"}, status),
        html.BUTTON({"data-testid": "detach-btn", "@click": detach}, "Detach"),
        html.BUTTON({"data-testid": "write-py-btn", "@click": write_py}, "Write via Python"),
        html.UL(
            {"data-testid": "event-list"},
            repeat(
                sequence=records,
                template=lambda record: html.LI({"data-testid": "storage-event"}, record),
            ),
        ),
    )
