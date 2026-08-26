from webcompy.components import ComponentContext, define_component
from webcompy.elements import html

from ...components.demo_display import DemoDisplay
from ...components.ui import DocsSection


@define_component()
def TransitionDemoPage(context: ComponentContext[None]):
    context.set_title("Transition - WebCompy Demo")
    return html.DIV(
        {"class": "page-container"},
        html.H1({"class": "page-title"}, "Transition"),
        html.P(
            {"class": "page-lead"},
            "Drives a Vue-compatible six-class CSS protocol around a single conditional "
            "child: the framework owns class timing and delayed DOM removal while users "
            "supply plain CSS.",
        ),
        DemoDisplay({"title": "Transition", "app_name": "transition", "demo_path": "/_demos/transition/app.py"}),
        DocsSection(
            {"heading": "Class protocol"},
            slots={
                "default": lambda: html.P(
                    {},
                    'Wrap a generator with Transition({"name": "fade"}, generator). When the '
                    "child appears the framework applies fade-enter-from, swaps to fade-enter-active "
                    "and fade-enter-to on the next frame, and removes all three classes when the "
                    "enter duration elapses. Disappearance is intercepted: fade-leave-from, then "
                    "fade-leave-active + fade-leave-to, and only then is the node removed.",
                )
            },
        ),
        DocsSection(
            {"heading": "Duration resolution"},
            slots={
                "default": lambda: html.P(
                    {},
                    "The duration resolves from the explicit duration prop (milliseconds) first, "
                    "then from the longest computed transition/animation duration of the node. When "
                    "neither yields a duration the sequence finishes immediately with a warning. "
                    "prefers-reduced-motion skips all sequences.",
                )
            },
        ),
        DocsSection(
            {"heading": "Single child"},
            slots={
                "default": lambda: html.P(
                    {},
                    "The generator yields at most one element (or None); replacing one visible "
                    "child with another runs leave first, then enter. A content update re-yielding "
                    "the same element type patches the node in place without restarting a running "
                    "sequence (during a leave, the update waits for the leave to finish, then "
                    "remounts and enters). Initial renders, SSR, and hydration show the steady "
                    "state without an appear animation.",
                )
            },
        ),
    )


TransitionDemoPage.scoped_style = {
    ".page-title": {
        "font-size": "var(--font-size-2xl)",
        "font-weight": "700",
        "margin-bottom": "var(--space-2)",
    },
    ".page-lead": {
        "color": "var(--color-fg-muted)",
        "margin-bottom": "var(--space-4)",
    },
}
