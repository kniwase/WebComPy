from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from ...components.demo_display import DemoDisplay
from ...templates.demo.matplotlib_sample import MatpoltlibSample


@define_component
def MatpoltlibSamplePage(_: ComponentContext[RouterContext]):
    return html.DIV(
        {},
        DemoDisplay(
            {
                "title": "Matplotlib Sample",
                "code": """
                    import base64
                    from io import BytesIO
                    import numpy as np
                    from matplotlib import pyplot as plt
                    from webcompy.elements import html, DOMEvent, DomNodeRef
                    from webcompy.components import define_component, ComponentContext
                    from webcompy.reactive import Reactive, computed


                    @define_component
                    def MatpoltlibSample(context: ComponentContext[None]):
                        input_ref = DomNodeRef()

                        fig, ax = plt.subplots()
                        x = np.linspace(-5, 5, 250)  # type: ignore
                        (line,) = ax.plot(x, np.array([0 for _ in x]))  # type: ignore

                        count = Reactive(15)

                        def on_change(ev: DOMEvent):
                            count.value = int(input_ref.node.value)

                        def add(ev: DOMEvent):
                            if count.value < 30:
                                count.value += 1
                                input_ref.node.value = str(count.value)

                        def pop(ev: DOMEvent):
                            if count.value > 1:
                                count.value -= 1
                                input_ref.node.value = str(count.value)

                        calc_square_wave = np.vectorize(
                            lambda x: np.vectorize(lambda k: (1 / (2 * k + 1)) * np.sin((2 * k + 1) * x))(
                                np.arange(count.value)  # type: ignore
                            ).sum()
                        )

                        @computed
                        def fig_data():
                            line.set_data(x, calc_square_wave(x))
                            ax.set_ylim(-2, 2)
                            fig.canvas.draw()
                            buffer = BytesIO()
                            fig.savefig(buffer, format="png")
                            return "data:image/png;base64,{}".format(
                                base64.b64encode(buffer.getvalue()).decode()
                            )

                        return html.DIV(
                            {},
                            html.H5({}, "Square Wave",),
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


                    MatpoltlibSample.scoped_style = {
                        "button": {
                            "display": "inline-block",
                            "text-decoration": "none",
                            "border": "solid 2px #668ad8",
                            "border-radius": "3px",
                            "transition": "0.2s",
                            "color": "black",
                            "width": "30px",
                        },
                        "button:hover": {
                            "background": "#668ad8",
                            "color": "white",
                        },
                        "input, img": {
                            "width": "100%",
                            "max-width": "600px",
                            "height": "auto",
                        },
                    }""",
            },
            slots={"component": lambda: MatpoltlibSample(None)},
        ),
    )
