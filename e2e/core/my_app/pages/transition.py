from webcompy.components import ComponentContext, define_component
from webcompy.elements import Teleport, Transition, html
from webcompy.signal import use_state


def _fade_box():
    return html.DIV({"data-testid": "fade-box", "class": "e2e-fade-box"}, "fade content")


def _slide_box():
    return html.DIV({"data-testid": "slide-box", "class": "e2e-slide-box"}, "slide content")


@define_component("transition-page")
def TransitionPage(context: ComponentContext[None]):
    context.set_title("Transition - E2E")
    fade_visible = use_state(lambda: False)
    slide_visible = use_state(lambda: False)

    def _toggle_fade(_ev):
        fade_visible.value = not fade_visible.value

    def _toggle_slide(_ev):
        slide_visible.value = not slide_visible.value

    return html.DIV(
        {"data-testid": "transition-page"},
        html.H2({}, "Transition Tests"),
        html.BUTTON({"data-testid": "toggle-fade", "@click": _toggle_fade}, "Toggle Fade"),
        html.BUTTON({"data-testid": "toggle-slide", "@click": _toggle_slide}, "Toggle Slide"),
        Transition({"name": "fade"}, lambda: _fade_box() if fade_visible.value else None),
        Teleport(
            {"to": "body"},
            Transition({"name": "slide"}, lambda: _slide_box() if slide_visible.value else None),
        ),
    )


TransitionPage.scoped_style = {
    ".e2e-fade-box": {
        "transition": "opacity 500ms ease",
    },
    ".fade-enter-from": {
        "opacity": "0",
    },
    ".fade-enter-active": {
        "transition": "opacity 500ms ease",
    },
    ".fade-enter-to": {
        "opacity": "1",
    },
    ".fade-leave-from": {
        "opacity": "1",
    },
    ".fade-leave-active": {
        "transition": "opacity 500ms ease",
    },
    ".fade-leave-to": {
        "opacity": "0",
    },
    ".e2e-slide-box": {
        "transform": "translateX(0)",
    },
    ".slide-enter-from": {
        "transform": "translateX(100%)",
    },
    ".slide-enter-active": {
        "transition": "transform 500ms ease",
    },
    ".slide-enter-to": {
        "transform": "translateX(0)",
    },
    ".slide-leave-from": {
        "transform": "translateX(0)",
    },
    ".slide-leave-active": {
        "transition": "transform 500ms ease",
    },
    ".slide-leave-to": {
        "transform": "translateX(-100%)",
    },
}
