"""Overlay components documentation page."""

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext
from webcompy.signal import use_state
from webcompy.template import load_markdown_document
from webcompy.ui import Drawer, Dropdown, Modal, ToastHost
from webcompy.ui.composables import use_toast

from ...components.docs_page import DOCS_PAGE_SCOPED_STYLE, docs_page_template


@define_component()
def OverlayDemo(context: ComponentContext[None]):
    modal_open = use_state(lambda: False)
    drawer_open = use_state(lambda: False)
    dropdown_open = use_state(lambda: False)
    push, toast_state = use_toast()

    def _open_modal(_e):
        modal_open.value = True

    def _close_modal():
        modal_open.value = False

    def _open_drawer(_e):
        drawer_open.value = True

    def _close_drawer():
        drawer_open.value = False

    def _close_dropdown():
        dropdown_open.value = False

    def _push_toast(_e):
        push("Saved successfully!", "success", 3.0)

    return html.DIV(
        {"class": "overlay-demo"},
        html.H3({}, "Modal"),
        html.BUTTON({"@click": _open_modal}, "Open Modal"),
        Modal(
            {"open": modal_open, "on_close": _close_modal, "aria_label": "Demo modal"},
            slots={
                "default": lambda: html.DIV(
                    {}, html.P({}, "Modal content"), html.BUTTON({"@click": lambda _e: _close_modal()}, "Close")
                )
            },
        ),
        html.H3({}, "Drawer"),
        html.BUTTON({"@click": _open_drawer}, "Open Drawer"),
        Drawer(
            {"open": drawer_open, "on_close": _close_drawer, "edge": "right", "aria_label": "Demo drawer"},
            slots={"default": lambda: html.DIV({}, "Drawer content")},
        ),
        html.H3({}, "Dropdown"),
        Dropdown(
            {"open": dropdown_open, "on_close": _close_dropdown},
            slots={
                "trigger": lambda: html.SPAN({}, "Open Menu"),
                "default": lambda: [
                    html.LI({"role": "menuitem"}, "Item 1"),
                    html.LI({"role": "menuitem"}, "Item 2"),
                ],
            },
        ),
        html.H3({}, "Toast"),
        html.BUTTON({"@click": _push_toast}, "Push Toast"),
        ToastHost({"toasts": toast_state.toasts, "on_dismiss": toast_state.dismiss, "on_remove": toast_state._remove}),
    )


OverlayDemo.scoped_style = {
    " .overlay-demo": {"display": "grid", "gap": "var(--space-3)", "margin": "var(--space-4) 0"},
}


@define_component()
async def OverlayPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/overlay.md")
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return docs_page_template(doc, context.props.path, extra_content=OverlayDemo({}))


OverlayPage.scoped_style = DOCS_PAGE_SCOPED_STYLE
