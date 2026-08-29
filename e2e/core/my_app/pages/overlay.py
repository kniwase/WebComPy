"""Overlay components E2E page."""

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import use_state
from webcompy.ui import Drawer, Dropdown, Modal, ToastHost
from webcompy.ui.composables import use_toast


@define_component()
def OverlayPage(context: ComponentContext[None]):
    """E2E page for overlay components."""

    context.set_title("Overlay - E2E")
    modal_open = use_state(lambda: False)
    drawer_open = use_state(lambda: False)
    dropdown_open = use_state(lambda: False)
    push, toast_state = use_toast()

    def _open_modal(_ev):
        modal_open.value = True

    def _close_modal():
        modal_open.value = False

    def _open_drawer(_ev):
        drawer_open.value = True

    def _close_drawer():
        drawer_open.value = False

    def _close_dropdown():
        dropdown_open.value = False

    def _push_toast(_ev):
        push("Toast message", "info", 5.0)

    def _push_long_toast(_ev):
        push("Long toast", "info", 10.0)

    return html.DIV(
        {"data-testid": "overlay-page"},
        html.H2({}, "Overlay Tests"),
        html.BUTTON({"data-testid": "open-modal", "@click": _open_modal}, "Open Modal"),
        Modal(
            {"open": modal_open, "on_close": _close_modal, "aria_label": "Test modal"},
            slots={
                "default": lambda: html.DIV(
                    {"data-testid": "modal-content"},
                    html.BUTTON({"data-testid": "modal-inner-btn"}, "Inner"),
                    html.BUTTON({}, "Second"),
                )
            },
        ),
        html.BUTTON({"data-testid": "open-drawer", "@click": _open_drawer}, "Open Drawer"),
        Drawer(
            {"open": drawer_open, "on_close": _close_drawer, "edge": "right", "aria_label": "Test drawer"},
            slots={"default": lambda: html.DIV({"data-testid": "drawer-content"}, "Drawer content")},
        ),
        html.DIV(
            {"data-testid": "dropdown-wrapper"},
            Dropdown(
                {"open": dropdown_open, "on_close": _close_dropdown},
                slots={
                    "trigger": lambda: html.SPAN({}, "Dropdown Trigger"),
                    "default": lambda: [
                        html.LI({"role": "menuitem", "data-testid": "dropdown-item-1", "tabindex": "0"}, "Item 1"),
                        html.LI({"role": "menuitem", "data-testid": "dropdown-item-2", "tabindex": "0"}, "Item 2"),
                        html.LI({"role": "menuitem", "data-testid": "dropdown-item-3", "tabindex": "0"}, "Item 3"),
                    ],
                },
            ),
        ),
        html.BUTTON({"data-testid": "push-toast", "@click": _push_toast}, "Push Toast"),
        html.BUTTON({"data-testid": "push-long-toast", "@click": _push_long_toast}, "Push Long Toast"),
        ToastHost({"toasts": toast_state.toasts, "on_dismiss": toast_state.dismiss, "on_remove": toast_state._remove}),
        html.DIV({"data-testid": "outside-area", "style": "height:100px;background:#eee;"}, "Outside"),
    )


OverlayPage.scoped_style = {
    " .webcompy-modal-panel": {"padding": "1rem"},
}
