import base64
from io import BytesIO

import numpy as np
from matplotlib import pyplot as plt

from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import DOMEvent, DomNodeRef, html
from webcompy.signal import use_computed, use_state


@define_component("matplotlib-sample-app")
def MatplotlibSample(context: ComponentContext[None]):
    input_ref = DomNodeRef()

    fig, ax = plt.subplots()
    x = np.linspace(-5, 5, 250)
    (line,) = ax.plot(x, np.array([0 for _ in x]))

    count = use_state(lambda: 15)

    def on_change(ev: DOMEvent):
        count.value = int(input_ref.value)

    def add(ev: DOMEvent):
        if count.value < 30:
            count.value += 1
            input_ref.value = str(count.value)

    def pop(ev: DOMEvent):
        if count.value > 1:
            count.value -= 1
            input_ref.value = str(count.value)

    calc_square_wave = np.vectorize(
        lambda x: np.vectorize(lambda k: (1 / (2 * k + 1)) * np.sin((2 * k + 1) * x))(np.arange(count.value)).sum()
    )

    @use_computed
    def fig_data():
        line.set_data(x, calc_square_wave(x))
        ax.set_ylim(-2, 2)
        fig.canvas.draw()
        buffer = BytesIO()
        fig.savefig(buffer, format="png")
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    return html.DIV(
        {"class": "matplotlib-demo"},
        html.H5(
            {},
            "Square Wave",
        ),
        html.P(
            {},
            "Value: ",
            count,
        ),
        html.P(
            {},
            html.INPUT(
                {
                    "@change": on_change,
                    ":ref": input_ref,
                    "type": "range",
                    "min": 1,
                    "max": 30,
                    "step": 1,
                    "value": count,
                }
            ),
        ),
        html.P(
            {},
            html.BUTTON(
                {"@click": add},
                "+",
            ),
            html.BUTTON(
                {"@click": pop},
                "-",
            ),
        ),
        html.IMG(
            {"src": fig_data},
        ),
    )


MatplotlibSample.scoped_style = {
    ".matplotlib-demo": {
        "padding": "var(--space-3)",
        "color": "var(--color-fg)",
    },
    "button": {
        "display": "inline-block",
        "text-decoration": "none",
        "border": "1px solid var(--color-accent)",
        "border-radius": "var(--radius-sm)",
        "transition": "background-color 0.15s ease, color 0.15s ease",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
        "width": "36px",
        "padding": "0.25rem 0",
        "margin-right": "var(--space-2)",
        "cursor": "pointer",
    },
    "button:hover": {
        "background": "var(--color-accent)",
        "color": "var(--color-on-accent)",
    },
    "input, img": {
        "width": "100%",
        "max-width": "600px",
        "height": "auto",
    },
    "img": {
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
    },
}

app = WebComPyApp(root_component=MatplotlibSample)
app.run()
