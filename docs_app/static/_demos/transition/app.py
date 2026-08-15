from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import Transition, html
from webcompy.signal import use_state


@define_component("transition-demo-app")
def TransitionDemoApp(_: ComponentContext[None]):
    fade_visible = use_state(lambda: False)
    slide_visible = use_state(lambda: False)

    def _toggle_fade(_ev):
        fade_visible.value = not fade_visible.value

    def _toggle_slide(_ev):
        slide_visible.value = not slide_visible.value

    return html.DIV(
        {"class": "transition-demo"},
        html.H1({}, "Transition Demo"),
        html.P({}, "Show and hide content; the CSS classes are driven by WebComPy."),
        html.DIV(
            {"class": "demo-controls"},
            html.BUTTON({"id": "toggle-fade", "@click": _toggle_fade}, "Toggle Fade"),
            html.BUTTON({"id": "toggle-slide", "@click": _toggle_slide}, "Toggle Slide"),
        ),
        Transition(
            {"name": "fade"},
            lambda: html.DIV({"class": "demo-fade-box"}, "Fade content") if fade_visible.value else None,
        ),
        Transition(
            {"name": "slide"},
            lambda: html.DIV({"class": "demo-slide-box"}, "Slide content") if slide_visible.value else None,
        ),
    )


TransitionDemoApp.scoped_style = {
    ".transition-demo": {
        "font-family": "sans-serif",
        "padding": "1rem",
    },
    ".demo-controls": {
        "display": "flex",
        "gap": "0.5rem",
        "margin-top": "1rem",
    },
    ".demo-controls button": {
        "padding": "0.5rem 1rem",
        "cursor": "pointer",
    },
    ".demo-fade-box": {
        "margin-top": "1rem",
        "padding": "1rem",
        "background": "mistyrose",
        "transition": "opacity 400ms ease",
    },
    ".fade-enter-from": {
        "opacity": "0",
    },
    ".fade-enter-active": {
        "transition": "opacity 400ms ease",
    },
    ".fade-enter-to": {
        "opacity": "1",
    },
    ".fade-leave-from": {
        "opacity": "1",
    },
    ".fade-leave-active": {
        "transition": "opacity 400ms ease",
    },
    ".fade-leave-to": {
        "opacity": "0",
    },
    ".demo-slide-box": {
        "margin-top": "1rem",
        "padding": "1rem",
        "background": "lightcyan",
        "transform": "translateX(0)",
    },
    ".slide-enter-from": {
        "transform": "translateX(100%)",
    },
    ".slide-enter-active": {
        "transition": "transform 400ms ease",
    },
    ".slide-enter-to": {
        "transform": "translateX(0)",
    },
    ".slide-leave-from": {
        "transform": "translateX(0)",
    },
    ".slide-leave-active": {
        "transition": "transform 400ms ease",
    },
    ".slide-leave-to": {
        "transform": "translateX(-100%)",
    },
}

app = WebComPyApp(root_component=TransitionDemoApp)
app.run()
